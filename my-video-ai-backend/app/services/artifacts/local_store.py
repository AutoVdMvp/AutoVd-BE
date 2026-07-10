import os
from app.core.config import settings

class LocalStore:
    """Owns project artifact paths under the local workspace root."""

    def __init__(self, root_dir: str = settings.WORKSPACE_DIR) -> None:
        self.root_dir = root_dir

    def project_dir(self, project_id: str) -> str:
        path = os.path.join(self.root_dir, project_id)
        os.makedirs(path, exist_ok=True)
        return path

    def image_path(self, project_id: str, scene_index: int) -> str:
        return os.path.join(self.project_dir(project_id), f"scene_{scene_index}.jpg")

    def audio_path(self, project_id: str, scene_index: int) -> str:
        return os.path.join(self.project_dir(project_id), f"scene_{scene_index}.mp3")

    def video_path(self, project_id: str) -> str:
        return os.path.join(self.project_dir(project_id), f"{project_id}_final.mp4")