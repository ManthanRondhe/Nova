import csv, os
from pymongo import MongoClient
from config import config


class CSVFallbackCollection:
    """Mock collection backed by local CSV/JSON files when MongoDB is offline."""
    def __init__(self, name, data_dir):
        self.name = name
        self.data_dir = data_dir
        self.csv_path = os.path.join(data_dir, f"{name}.csv")

    def _read_rows(self):
        if not os.path.exists(self.csv_path):
            return []
        try:
            import json as _json
            with open(self.csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = []
                for r in reader:
                    row = dict(r)
                    # Attempt to deserialize JSON-encoded or Python-literal complex fields
                    for k, v in row.items():
                        if isinstance(v, str) and v.startswith(("[", "{")):
                            try:
                                row[k] = _json.loads(v)
                            except (ValueError, _json.JSONDecodeError):
                                try:
                                    import ast
                                    row[k] = ast.literal_eval(v)
                                except Exception:
                                    pass
                    rows.append(row)
                return rows
        except Exception:
            return []

    def _write_rows(self, rows):
        if not rows:
            return
        # Collect ALL unique field names across every row so new columns aren't lost
        seen = set()
        fieldnames = []
        for r in rows:
            for k in r.keys():
                if k not in seen:
                    seen.add(k)
                    fieldnames.append(k)
        # Serialize complex values (lists, dicts) to JSON strings for CSV storage
        import json as _json
        serialized = []
        for r in rows:
            row = {}
            for k in fieldnames:
                v = r.get(k, "")
                if isinstance(v, (list, dict)):
                    row[k] = _json.dumps(v, default=str)
                else:
                    row[k] = v
            serialized.append(row)
        try:
            with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(serialized)
        except Exception:
            pass

    def find(self, query=None, projection=None):
        rows = self._read_rows()
        if not query:
            return rows
        filtered = []
        for r in rows:
            match = True
            for k, v in query.items():
                if str(r.get(k, "")) != str(v):
                    match = False
                    break
            if match:
                filtered.append(r)
        return filtered

    def find_one(self, query=None, projection=None):
        results = self.find(query, projection)
        return results[0] if results else None

    def insert_many(self, docs):
        rows = self._read_rows()
        rows.extend([dict(d) for d in docs])
        self._write_rows(rows)

    def insert_one(self, doc):
        rows = self._read_rows()
        rows.append(dict(doc))
        self._write_rows(rows)

    def delete_many(self, query=None):
        if not query:
            if os.path.exists(self.csv_path):
                try:
                    with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
                        pass
                except Exception:
                    pass
        else:
            rows = self._read_rows()
            kept = [r for r in rows if not all(str(r.get(k, "")) == str(v) for k, v in query.items())]
            self._write_rows(kept)

    def update_one(self, query, update, upsert=False):
        rows = self._read_rows()
        matched = False
        set_vals = update.get("$set", {}) if isinstance(update, dict) else update
        for r in rows:
            if all(str(r.get(k, "")) == str(v) for k, v in query.items()):
                r.update(set_vals)
                matched = True
                break
        if not matched and upsert:
            new_row = {**query, **set_vals}
            rows.append(new_row)
        self._write_rows(rows)


class CSVFallbackDB:
    """Mock database that returns CSVFallbackCollection for any collection attribute."""
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.name = "local_csv_fallback"

    def __getattr__(self, name):
        return CSVFallbackCollection(name, self.data_dir)

    def __getitem__(self, name):
        return CSVFallbackCollection(name, self.data_dir)


client = None
db = None

def get_db():
    global client, db
    if db is not None:
        return db
        
    if not config.MONGO_URI:
        print("[!] MONGO_URI is missing, using local CSV fallback.")
        return CSVFallbackDB(config.DATA_DIR)
        
    try:
        client = MongoClient(config.MONGO_URI, serverSelectionTimeoutMS=2000)
        # Check connection
        client.admin.command('ping')
        
        # Safely determine database name
        try:
            default_db = client.get_default_database()
            db = default_db if default_db is not None else client["nova"]
        except Exception:
            db = client["nova"]
            
        print(f"[+] Successfully connected to MongoDB database: {db.name}")
        return db
    except Exception as e:
        print(f"[!] MongoDB unavailable ({e}). Activating CSV file fallback.")
        return CSVFallbackDB(config.DATA_DIR)

# Export the DB instance
db = get_db()

