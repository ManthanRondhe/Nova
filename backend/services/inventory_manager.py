"""
AutoMech AI - Inventory Manager
Tracks spare parts stock, detects low levels, manages restocking.
"""
import csv, os
from datetime import datetime

from database import db

class InventoryManager:
    def __init__(self, data_dir):
        self.collection = db.inventory
        self.parts_file = os.path.join(data_dir, "spare_parts.csv")
        self.headers = ["part_id","part_name","category","current_stock","min_stock_level","unit_price","last_restocked","location_in_garage"]
    
    def _read_inventory(self):
        return list(self.collection.find({}, {"_id": 0}))
    
    def _write_inventory(self, rows):
        self.collection.delete_many({})
        if rows:
            self.collection.insert_many([{**r} for r in rows])
    
    def get_all_inventory(self):
        """Get complete inventory."""
        return self._read_inventory()
    
    def get_part_stock(self, part_id):
        """Get stock info for a specific part."""
        rows = self._read_inventory()
        for r in rows:
            if r["part_id"] == part_id:
                return r
        return None
    
    def check_parts_availability(self, part_ids_str):
        """Check if required parts are in stock. Returns available and missing parts."""
        if not part_ids_str:
            return {"available": [], "missing": [], "all_available": True}
        
        part_ids = [p.strip() for p in part_ids_str.split(",")]
        rows = self._read_inventory()
        inventory_map = {r["part_id"]: r for r in rows}
        
        available = []
        missing = []
        
        for pid in part_ids:
            if pid in inventory_map:
                stock = int(inventory_map[pid].get("current_stock", 0))
                item = inventory_map[pid].copy()
                if stock > 0:
                    available.append(item)
                else:
                    missing.append(item)
            else:
                missing.append({"part_id": pid, "part_name": "Unknown Part", "current_stock": 0})
        
        return {
            "available": available,
            "missing": missing,
            "all_available": len(missing) == 0
        }
    
    def deduct_stock(self, part_id, quantity=1):
        """Deduct stock after using parts for a job."""
        rows = self._read_inventory()
        for r in rows:
            if r["part_id"] == part_id:
                current = int(r.get("current_stock", 0))
                r["current_stock"] = str(max(0, current - quantity))
                self._write_inventory(rows)
                return r
        return None
    
    def add_stock(self, part_id, quantity):
        """Add stock when parts arrive."""
        rows = self._read_inventory()
        for r in rows:
            if r["part_id"] == part_id:
                current = int(r.get("current_stock", 0))
                r["current_stock"] = str(current + quantity)
                r["last_restocked"] = datetime.now().strftime("%Y-%m-%d")
                self._write_inventory(rows)
                return r
        return None
    
    def get_low_stock_alerts(self):
        """Get all parts below minimum stock level."""
        rows = self._read_inventory()
        alerts = []
        for r in rows:
            current = int(r.get("current_stock", 0))
            minimum = int(r.get("min_stock_level", 0))
            if minimum > 0 and current <= minimum:
                r["deficit"] = str(minimum - current + 2)  # Order minimum + 2 extra
                alerts.append(r)
        return alerts
    
    def search_parts(self, query):
        """Search inventory by name or category."""
        rows = self._read_inventory()
        query_lower = query.lower()
        return [r for r in rows if query_lower in r.get("part_name","").lower() 
                or query_lower in r.get("category","").lower()
                or query_lower in r.get("part_id","").lower()]
    
    def get_inventory_stats(self):
        """Get inventory statistics."""
        rows = self._read_inventory()
        total_items = len(rows)
        total_stock = sum(int(r.get("current_stock", 0)) for r in rows)
        low_stock = len(self.get_low_stock_alerts())
        out_of_stock = len([r for r in rows if int(r.get("current_stock", 0)) == 0 and int(r.get("min_stock_level", 0)) > 0])
        total_value = sum(int(r.get("current_stock", 0)) * int(r.get("unit_price", 0)) for r in rows)
        
        return {
            "total_items": total_items,
            "total_stock_units": total_stock,
            "low_stock_count": low_stock,
            "out_of_stock_count": out_of_stock,
            "total_inventory_value": total_value
        }
    
    def get_parts_catalog(self):
        """Get spare parts catalog."""
        rows = []
        try:
            with open(self.parts_file, "r", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    rows.append(row)
        except FileNotFoundError:
            pass
        return rows
