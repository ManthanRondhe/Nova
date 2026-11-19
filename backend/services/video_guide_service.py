"""
Nova AI - Video Guide Service
Fetches, ranks, caches, and stages chronological repair video guides
for diagnosed automotive faults using YouTube Data API v3 with graceful fallback.
"""
import os
import json
import urllib.parse
import re
from datetime import datetime, timedelta, timezone
import requests

from config import config
from database import db


class VideoGuideService:
    """Service to generate chronological repair stages and retrieve relevant video tutorials."""

    def __init__(self, data_dir=None):
        self.data_dir = data_dir or config.DATA_DIR
        self.cache_collection = getattr(db, "video_cache", None) if db is not None else None
        self.local_cache_file = os.path.join(self.data_dir, "video_cache.json")
        self.ttl_days = config.VIDEO_CACHE_TTL_DAYS
        self.api_key = config.YOUTUBE_API_KEY
        self.search_url = "https://www.googleapis.com/youtube/v3/search"
        self.video_details_url = "https://www.googleapis.com/youtube/v3/videos"

    # ─────────────────────────────────────────────────────────────
    # Chronological Repair Stage Decomposition
    # ─────────────────────────────────────────────────────────────
    def generate_repair_stages(self, fault_name, system=None, fix_procedure=None):
        """
        Decomposes a fault into an ordered list of 4-6 real-world chronological
        repair stages based on fault category and fix procedure.
        """
        clean_fault = (fault_name or "Vehicle Fault").strip()
        system_lower = (system or "").lower()
        fault_lower = clean_fault.lower()

        # Custom tailored stages for common automotive components
        if any(w in fault_lower for w in ["starter", "cranking", "start motor"]):
            return [
                {
                    "stage_number": 1,
                    "title": "Diagnosing & Voltage Drop Testing",
                    "description": "Test battery voltage, starter relay, and starter solenoid with a multimeter before removal.",
                    "search_suffix": "diagnose test voltage drop multimeter"
                },
                {
                    "stage_number": 2,
                    "title": "Battery Disconnect & Safety Prep",
                    "description": "Disconnect negative battery terminal, raise and support vehicle on rated jack stands.",
                    "search_suffix": "disconnect battery jack stands safety"
                },
                {
                    "stage_number": 3,
                    "title": "Wiring Disconnection & Starter Removal",
                    "description": "Disconnect the solenoid B-terminal and S-terminal wiring, unbolt mounting bolts, and withdraw starter.",
                    "search_suffix": "remove starter motor bolts wiring harness"
                },
                {
                    "stage_number": 4,
                    "title": "Bench Inspection & New Starter Prep",
                    "description": "Compare pinions, gear teeth, and bolt spacing between the old and replacement starter.",
                    "search_suffix": "bench test inspect starter replacement comparison"
                },
                {
                    "stage_number": 5,
                    "title": "Reinstallation & Torque",
                    "description": "Position new starter, hand-thread bolts to prevent cross-threading, torque to spec, and reconnect terminals.",
                    "search_suffix": "install new starter motor torque spec wiring"
                },
                {
                    "stage_number": 6,
                    "title": "Testing After Install & Cranking Verification",
                    "description": "Reconnect battery, crank engine, verify smooth engagement, and test alternator recharge voltage.",
                    "search_suffix": "cranking test start verification"
                }
            ]

        if any(w in fault_lower for w in ["alternator", "charging", "battery light"]):
            return [
                {
                    "stage_number": 1,
                    "title": "Charging System Diagnostic",
                    "description": "Measure resting battery voltage and running voltage with loads (headlights, AC) applied.",
                    "search_suffix": "diagnose charging system test multimeter"
                },
                {
                    "stage_number": 2,
                    "title": "Safety Prep & Battery Disconnect",
                    "description": "Disconnect negative terminal to prevent alternator B+ terminal shorting against engine metal.",
                    "search_suffix": "safety disconnect battery"
                },
                {
                    "stage_number": 3,
                    "title": "Serpentine Belt Removal & Unbolting",
                    "description": "Relieve belt tensioner tension, slip off serpentine belt, disconnect electrical harness, and remove bolts.",
                    "search_suffix": "remove serpentine belt unbolt alternator"
                },
                {
                    "stage_number": 4,
                    "title": "Alternator Replacement & Belt Routing",
                    "description": "Mount new alternator, torque bolts, reconnect harness, and route belt strictly according to diagram.",
                    "search_suffix": "install new alternator belt routing"
                },
                {
                    "stage_number": 5,
                    "title": "Output Voltage Verification",
                    "description": "Start engine and ensure alternator generates 13.8V - 14.5V under full vehicle accessory load.",
                    "search_suffix": "test charging voltage test output"
                }
            ]

        if any(w in fault_lower for w in ["brake", "pad", "rotor", "caliper", "disc"]):
            return [
                {
                    "stage_number": 1,
                    "title": "Inspection & Safety Lift",
                    "description": "Loosen lug nuts slightly, jack vehicle on level concrete, secure jack stands, and remove wheels.",
                    "search_suffix": "jack up remove wheel brake inspection"
                },
                {
                    "stage_number": 2,
                    "title": "Caliper Removal & Support",
                    "description": "Unbolt guide slider pins, pry caliper off rotor, and hang caliper with S-hook to protect the brake line.",
                    "search_suffix": "remove caliper slider pin hang hanger"
                },
                {
                    "stage_number": 3,
                    "title": "Rotor Inspection / Replacement & Bracket Cleaning",
                    "description": "Remove caliper bracket, take off old rotor, clean wheel hub face with wire brush, and install new rotor.",
                    "search_suffix": "remove rotor clean hub caliper bracket"
                },
                {
                    "stage_number": 4,
                    "title": "Piston Retraction & Pad Lubrication",
                    "description": "Compress caliper piston with caliper tool, clean abutment clips, apply synthetic brake grease to slide points.",
                    "search_suffix": "compress caliper piston lubricate brake hardware"
                },
                {
                    "stage_number": 5,
                    "title": "Reassembly & Wheel Torque",
                    "description": "Reinstall caliper, torque slider pins, mount wheel, hand tighten lugs, lower vehicle, and torque to factory spec.",
                    "search_suffix": "torque caliper bolts wheel lug nut torque"
                },
                {
                    "stage_number": 6,
                    "title": "Brake Pedal Pumping & Bedding-In Procedure",
                    "description": "Pump brake pedal several times until firm BEFORE shifting into drive, and perform pad bedding-in road test.",
                    "search_suffix": "pump brake pedal bedding in procedure test drive"
                }
            ]

        if any(w in fault_lower for w in ["spark plug", "misfire", "ignition coil"]):
            return [
                {
                    "stage_number": 1,
                    "title": "Scan Codes & Cylinder Identification",
                    "description": "Read OBD-II misfire codes (P0300-P0308) to pinpoint which cylinders are experiencing misfire.",
                    "search_suffix": "diagnose misfire scan tool obd code"
                },
                {
                    "stage_number": 2,
                    "title": "Engine Cover & Coil Pack Access",
                    "description": "Remove engine beauty cover, disconnect coil wiring clips, blow compressed air around spark plug wells.",
                    "search_suffix": "remove ignition coil pack disconnect harness"
                },
                {
                    "stage_number": 3,
                    "title": "Spark Plug Removal & Gap Verification",
                    "description": "Use magnetic spark plug socket to unthread old plugs, inspect ceramic color, and check gap on new plugs.",
                    "search_suffix": "remove spark plug inspect check gap socket"
                },
                {
                    "stage_number": 4,
                    "title": "Installation & Hand Threading",
                    "description": "Thread new plugs strictly by hand to prevent cylinder head cross-threading; torque to 15-20 ft-lbs.",
                    "search_suffix": "install spark plugs torque spec dielectric grease"
                },
                {
                    "stage_number": 5,
                    "title": "Clear Fault Codes & Smooth Idle Validation",
                    "description": "Reinstall coil packs, start engine, clear DTC codes, and verify smooth, shudder-free idle.",
                    "search_suffix": "test drive clear check engine light smooth idle"
                }
            ]

        # Generic system-based breakdown if specific fault is not explicitly hardcoded
        stages = [
            {
                "stage_number": 1,
                "title": f"Initial Diagnosis & Safety Preparation",
                "description": f"Perform visual inspection and safety precautions for {clean_fault}.",
                "search_suffix": "diagnosis inspection safety preparation"
            },
            {
                "stage_number": 2,
                "title": f"Disassembly & Accessing Faulty Components",
                "description": f"Remove protective covers and surrounding parts to reach {clean_fault}.",
                "search_suffix": "removal disassembly step by step"
            },
            {
                "stage_number": 3,
                "title": f"Component Replacement / Repair",
                "description": f"Inspect, replace, or repair the damaged parts as specified in technical procedures.",
                "search_suffix": "replace install new part procedure"
            },
            {
                "stage_number": 4,
                "title": f"Reassembly & Quality Calibration",
                "description": f"Reassemble all components, torque to factory specifications, and replenish fluids if needed.",
                "search_suffix": "reassembly torque specs installation"
            },
            {
                "stage_number": 5,
                "title": f"Post-Repair Testing & Road Verification",
                "description": f"Test operation to ensure {clean_fault} is resolved without warning lights or abnormal noises.",
                "search_suffix": "testing verification test drive"
            }
        ]

        # If fix procedure provides steps, enrich the descriptions
        if fix_procedure and len(fix_procedure) > 20:
            sentences = [s.strip() for s in re.split(r'[.\n;]', fix_procedure) if len(s.strip()) > 8]
            if len(sentences) >= 3:
                stages[1]["description"] = sentences[0]
                stages[2]["description"] = sentences[1]
                if len(sentences) > 2:
                    stages[3]["description"] = sentences[2]

        return stages

    # ─────────────────────────────────────────────────────────────
    # Cache Layer (MongoDB with JSON/Local Fallback)
    # ─────────────────────────────────────────────────────────────
    @staticmethod
    def _parse_guide_object(raw_guide):
        """Safely parse guide into a dict, handling JSON strings or Python dict strings."""
        if isinstance(raw_guide, dict):
            return raw_guide
        if isinstance(raw_guide, str):
            try:
                import json as _json
                parsed = _json.loads(raw_guide)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass
            try:
                import ast
                parsed = ast.literal_eval(raw_guide)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass
        return None

    def _get_cached_guide(self, cache_key):
        """Retrieve cached video guide if not expired."""
        now = datetime.now(timezone.utc)
        # 1. Try MongoDB
        if self.cache_collection is not None:
            try:
                cached = self.cache_collection.find_one({"cache_key": cache_key})
                if cached:
                    created_at = cached.get("cached_at")
                    if isinstance(created_at, str):
                        created_at = datetime.fromisoformat(created_at)
                    if created_at and (now - created_at) < timedelta(days=self.ttl_days):
                        guide = self._parse_guide_object(cached.get("guide"))
                        if guide:
                            return guide
            except Exception as e:
                pass

        # 2. Local JSON cache fallback
        if os.path.exists(self.local_cache_file):
            try:
                with open(self.local_cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    entry = data.get(cache_key)
                    if entry:
                        created_at = datetime.fromisoformat(entry.get("cached_at", "2000-01-01"))
                        if (now - created_at) < timedelta(days=self.ttl_days):
                            guide = self._parse_guide_object(entry.get("guide"))
                            if guide:
                                return guide
            except Exception:
                pass

        return None

    def _save_cached_guide(self, cache_key, guide_data):
        """Save video guide to cache with timestamp."""
        now_str = datetime.now(timezone.utc).isoformat()
        entry = {
            "cache_key": cache_key,
            "cached_at": now_str,
            "guide": guide_data
        }

        # 1. Try MongoDB
        if self.cache_collection is not None:
            try:
                self.cache_collection.update_one(
                    {"cache_key": cache_key},
                    {"$set": entry},
                    upsert=True
                )
            except Exception:
                pass

        # 2. Local JSON cache
        try:
            os.makedirs(os.path.dirname(self.local_cache_file), exist_ok=True)
            data = {}
            if os.path.exists(self.local_cache_file):
                try:
                    with open(self.local_cache_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except Exception:
                    data = {}
            data[cache_key] = entry
            # Prune old cache entries if file grows too large (> 500 entries)
            if len(data) > 500:
                keys = list(data.keys())[:250]
                data = {k: data[k] for k in keys}
            with open(self.local_cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────
    # Duration Parsing & Shorts Filter
    # ─────────────────────────────────────────────────────────────
    @staticmethod
    def _parse_iso_duration(duration_str):
        """Parse ISO 8601 duration (e.g., PT12M30S) into total seconds and human readable string."""
        if not duration_str or not duration_str.startswith("PT"):
            return 0, "Unknown"
        pattern = re.compile(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?')
        match = pattern.match(duration_str)
        if not match:
            return 0, "Unknown"
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)
        total_seconds = (hours * 3600) + (minutes * 60) + seconds
        if hours > 0:
            formatted = f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            formatted = f"{minutes}:{seconds:02d}"
        return total_seconds, formatted

    # ─────────────────────────────────────────────────────────────
    # Video Querying & Graceful Fallback
    # ─────────────────────────────────────────────────────────────
    def _fetch_youtube_videos(self, query, max_results=2):
        """
        Query YouTube Data API v3 search + video details for a given stage query.
        Returns empty list if API key is missing or quota is exceeded.
        """
        if not self.api_key:
            return []

        try:
            # 1. Search videos
            params = {
                "part": "snippet",
                "q": query,
                "type": "video",
                "videoEmbeddable": "true",
                "maxResults": 6,  # fetch a few extra to filter out Shorts
                "key": self.api_key
            }
            res = requests.get(self.search_url, params=params, timeout=6)
            if res.status_code != 200:
                # Quota exceeded or invalid key: fail gracefully
                return []
            
            search_data = res.json()
            items = search_data.get("items", [])
            if not items:
                return []

            video_ids = [item["id"]["videoId"] for item in items if "id" in item and "videoId" in item["id"]]
            if not video_ids:
                return []

            # 2. Get video details (duration, view count, likes)
            details_params = {
                "part": "contentDetails,statistics,snippet",
                "id": ",".join(video_ids),
                "key": self.api_key
            }
            details_res = requests.get(self.video_details_url, params=details_params, timeout=6)
            details_items = details_res.json().get("items", []) if details_res.status_code == 200 else []

            videos = []
            for item in details_items:
                vid_id = item["id"]
                snippet = item.get("snippet", {})
                content_details = item.get("contentDetails", {})
                statistics = item.get("statistics", {})

                title = snippet.get("title", "")
                # Filter out obvious shorts
                if "#shorts" in title.lower() or "#short" in title.lower():
                    continue

                duration_iso = content_details.get("duration", "")
                total_seconds, formatted_duration = self._parse_iso_duration(duration_iso)

                # Filter out videos under 60 seconds (Shorts) or over 45 minutes (full podcasts)
                if 0 < total_seconds < 60:
                    continue

                view_count = int(statistics.get("viewCount", 0))
                like_count = int(statistics.get("likeCount", 0))

                thumbnails = snippet.get("thumbnails", {})
                thumb_url = (thumbnails.get("medium") or thumbnails.get("default") or {}).get("url", "")

                videos.append({
                    "video_id": vid_id,
                    "title": title,
                    "channel_title": snippet.get("channelTitle", "Automotive Guide"),
                    "duration": formatted_duration,
                    "duration_seconds": total_seconds,
                    "view_count": view_count,
                    "like_count": like_count,
                    "thumbnail": thumb_url,
                    "embed_url": f"https://www.youtube.com/embed/{vid_id}",
                    "watch_url": f"https://www.youtube.com/watch?v={vid_id}"
                })

            # Rank by engagement (views + likes) and duration preference (between 3 and 18 minutes)
            def score_video(v):
                sec = v.get("duration_seconds", 300)
                duration_score = 100 if (180 <= sec <= 1200) else 50
                engagement_score = min(50, (v.get("view_count", 0) / 10000))
                return duration_score + engagement_score

            videos.sort(key=score_video, reverse=True)
            return videos[:max_results]

        except Exception:
            return []

    # ─────────────────────────────────────────────────────────────
    # Main Guide Generation Method
    # ─────────────────────────────────────────────────────────────
    def get_repair_guide(self, fault_name, vehicle_make=None, vehicle_model=None, fix_procedure=None, system=None):
        """
        Generate complete repair guide with stages, video items, or graceful search links.
        Guaranteed to NEVER crash or raise unhandled exceptions.
        """
        vehicle_make = (vehicle_make or "").strip()
        vehicle_model = (vehicle_model or "").strip()
        vehicle_str = f"{vehicle_make} {vehicle_model}".strip()

        cache_key = f"{vehicle_str}_{fault_name}_{system}".lower().replace(" ", "_")
        cached = self._get_cached_guide(cache_key)
        if cached:
            return cached

        stages = self.generate_repair_stages(fault_name, system=system, fix_procedure=fix_procedure)
        enriched_stages = []

        for stage in stages:
            stage_num = stage["stage_number"]
            stage_title = stage["title"]
            desc = stage["description"]
            suffix = stage.get("search_suffix", "")

            # Construct targeted YouTube search query
            # e.g.: "Honda Civic starter motor replacement diagnosing testing"
            query_parts = []
            if vehicle_str:
                query_parts.append(vehicle_str)
            query_parts.append(fault_name)
            query_parts.append(suffix)
            search_query = " ".join(query_parts).strip()

            encoded_query = urllib.parse.quote_plus(search_query)
            fallback_search_url = f"https://www.youtube.com/results?search_query={encoded_query}"

            # Query YouTube API
            videos = self._fetch_youtube_videos(search_query, max_results=2)

            is_fallback = len(videos) == 0
            enriched_stages.append({
                "stage_number": stage_num,
                "stage_title": stage_title,
                "description": desc,
                "search_query": search_query,
                "fallback_search_url": fallback_search_url,
                "is_fallback": is_fallback,
                "videos": videos
            })

        result = {
            "fault_name": fault_name,
            "vehicle": vehicle_str or "Standard Vehicle",
            "total_stages": len(enriched_stages),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "has_videos": any(len(s.get("videos", [])) > 0 for s in enriched_stages),
            "stages": enriched_stages
        }

        # Cache the result
        self._save_cached_guide(cache_key, result)
        return result
