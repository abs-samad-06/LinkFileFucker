"""
File storage management module.
Handles file metadata, key generation, and persistence.
"""

import json
import secrets
import os
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

STORAGE_FILE = "file_storage.json"
STORAGE_DIR = Path("data")
STORAGE_DIR.mkdir(exist_ok=True)


@dataclass
class FileMetadata:
    """Represents stored file metadata"""
    file_key: str
    file_id: str
    file_name: str
    file_size: int
    user_id: int
    message_id_in_storage: int
    has_password: bool
    password: Optional[str] = None
    created_at: str = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()


class FileStorage:
    """Manages file metadata persistence"""
    
    def __init__(self):
        self.db_path = STORAGE_DIR / STORAGE_FILE
        self.data: Dict[str, FileMetadata] = {}
        self._load()
    
    def _load(self):
        """Load metadata from disk"""
        if self.db_path.exists():
            with open(self.db_path, "r") as f:
                raw = json.load(f)
                self.data = {
                    k: FileMetadata(**v) for k, v in raw.items()
                }
    
    def _save(self):
        """Persist metadata to disk"""
        with open(self.db_path, "w") as f:
            json.dump(
                {k: asdict(v) for k, v in self.data.items()},
                f,
                indent=2
            )
    
    def generate_file_key(self) -> str:
        """Generate unique file key"""
        return secrets.token_urlsafe(16)
    
    def store_file(self, file_metadata: FileMetadata) -> str:
        """
        Store file metadata, return file_key.
        
        Args:
            file_metadata: FileMetadata object with all required fields
            
        Returns:
            file_key: Unique identifier for the file
        """
        key = file_metadata.file_key
        self.data[key] = file_metadata
        self._save()
        return key
    
    def get_file(self, file_key: str) -> Optional[FileMetadata]:
        """Retrieve file metadata by key"""
        return self.data.get(file_key)
    
    def update_password(self, file_key: str, password: str) -> bool:
        """Update password for a file"""
        if file_key in self.data:
            self.data[file_key].password = password
            self.data[file_key].has_password = True
            self._save()
            return True
        return False
    
    def delete_file(self, file_key: str) -> bool:
        """Delete file metadata"""
        if file_key in self.data:
            del self.data[file_key]
            self._save()
            return True
        return False
    
    def get_user_files(self, user_id: int) -> list[FileMetadata]:
        """Get all files for a user"""
        return [
            metadata for metadata in self.data.values()
            if metadata.user_id == user_id
        ]


# Global storage instance
storage = FileStorage()
