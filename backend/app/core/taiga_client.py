"""Taiga API Client for project management integration."""
import logging
from typing import Optional, List, Dict, Any, Union
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class TaigaClient:
    """Client for interacting with Taiga API."""

    def __init__(
        self,
        base_url: str = None,
        auth_token: str = None,
        username: str = None,
        password: str = None,
        project_id: Union[int, str] = None
    ):
        self.base_url = (base_url or settings.TAIGA_URL).rstrip("/")
        self._auth_token = auth_token or settings.TAIGA_AUTH_TOKEN
        self._username = username or settings.TAIGA_USERNAME
        self._password = password or settings.TAIGA_PASSWORD
        # project_id can be int (ID) or str (slug like "tecq-ai-bd")
        self._project_id_or_slug = project_id or settings.TAIGA_PROJECT_SLUG or settings.TAIGA_PROJECT_ID
        self._resolved_project_id: Optional[int] = None

    @property
    def project_id(self) -> Optional[int]:
        """Get resolved project ID."""
        return self._resolved_project_id

    async def _ensure_authenticated(self) -> str:
        """Ensure we have an auth token, login if needed."""
        if self._auth_token:
            return self._auth_token

        if self._username and self._password:
            self._auth_token = await self._login()
            return self._auth_token

        raise ValueError("No auth token or username/password configured for Taiga")

    async def _login(self) -> str:
        """Login to Taiga with username/password and get auth token."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/v1/auth",
                    headers={"Content-Type": "application/json"},
                    json={
                        "type": "normal",
                        "username": self._username,
                        "password": self._password,
                    },
                )
                response.raise_for_status()
                data = response.json()
                token = data.get("auth_token")
                if not token:
                    raise ValueError("No auth_token in login response")
                logger.info(f"Successfully logged in to Taiga as {self._username}")
                return token
            except httpx.HTTPStatusError as e:
                logger.error(f"Taiga login failed: {e.response.status_code} - {e.response.text}")
                raise ValueError(f"Taiga login failed: {e.response.text}")
            except Exception as e:
                logger.error(f"Taiga login error: {e}")
                raise

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests."""
        return {
            "Authorization": f"Bearer {self._auth_token}",
            "Content-Type": "application/json",
        }

    async def resolve_project_id(self) -> Optional[int]:
        """Resolve project slug to numeric ID if needed."""
        if self._resolved_project_id:
            return self._resolved_project_id

        if isinstance(self._project_id_or_slug, int) and self._project_id_or_slug > 0:
            self._resolved_project_id = self._project_id_or_slug
            return self._resolved_project_id

        if isinstance(self._project_id_or_slug, str) and self._project_id_or_slug:
            # It's a slug, resolve it
            project = await self.get_project_by_slug(self._project_id_or_slug)
            if project:
                self._resolved_project_id = project.get("id")
                return self._resolved_project_id

        return None

    async def get_project_by_slug(self, slug: str) -> Optional[Dict]:
        """Get project by slug (e.g., 'tecq-ai-bd')."""
        try:
            return await self._request("GET", f"/projects/by_slug?slug={slug}")
        except Exception as e:
            logger.error(f"Failed to get project by slug '{slug}': {e}")
            return None

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> Optional[Dict]:
        """Make an API request to Taiga."""
        # Ensure we're authenticated before making requests
        await self._ensure_authenticated()

        url = f"{self.base_url}/api/v1{endpoint}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=self._get_headers(),
                    json=data,
                    params=params,
                )
                response.raise_for_status()
                return response.json() if response.content else None
            except httpx.HTTPStatusError as e:
                logger.error(f"Taiga API error: {e.response.status_code} - {e.response.text}")
                raise
            except Exception as e:
                logger.error(f"Taiga request failed: {e}")
                raise

    async def get_project(self, project_id: int = None) -> Optional[Dict]:
        """Get project details."""
        pid = project_id or await self.resolve_project_id()
        if not pid:
            raise ValueError("Project ID not configured. Set TAIGA_PROJECT_SLUG or TAIGA_PROJECT_ID.")
        return await self._request("GET", f"/projects/{pid}")

    async def get_project_statuses(self, project_id: int = None) -> List[Dict]:
        """Get user story statuses for a project."""
        pid = project_id or await self.resolve_project_id()
        if not pid:
            return []
        try:
            statuses = await self._request("GET", "/userstory-statuses", params={"project": pid})
            return statuses or []
        except Exception as e:
            logger.error(f"Failed to get project statuses: {e}")
            return []

    async def get_user_story(self, story_id: int) -> Optional[Dict]:
        """Get a specific user story."""
        return await self._request("GET", f"/userstories/{story_id}")

    async def create_user_story(
        self,
        subject: str,
        description: str = None,
        project_id: int = None,
        status_id: int = None,
        tags: List[str] = None,
        due_date: str = None,
    ) -> Optional[Dict]:
        """Create a new user story in Taiga.

        Args:
            subject: The title of the user story
            description: Detailed description
            project_id: Taiga project ID (uses default if not provided)
            status_id: Taiga status ID
            tags: List of tags to apply
            due_date: Due date in ISO format (YYYY-MM-DD)
        """
        pid = project_id or await self.resolve_project_id()
        if not pid:
            raise ValueError("Project ID not configured")
        data = {
            "project": pid,
            "subject": subject,
        }
        if description:
            data["description"] = description
        if status_id:
            data["status"] = status_id
        if tags:
            data["tags"] = tags
        if due_date:
            data["due_date"] = due_date

        return await self._request("POST", "/userstories", data=data)

    async def update_user_story_status(self, story_id: int, status_id: int, version: int) -> Optional[Dict]:
        """Update user story status."""
        data = {
            "status": status_id,
            "version": version,
        }
        return await self._request("PATCH", f"/userstories/{story_id}", data=data)

    async def update_user_story(
        self,
        story_id: int,
        version: int,
        description: str = None,
        subject: str = None,
        status_id: int = None,
        tags: List[str] = None,
        due_date: str = None,
    ) -> Optional[Dict]:
        """Update a user story with multiple fields.

        Args:
            story_id: The Taiga story ID
            version: Current version for optimistic locking
            description: New description (optional)
            subject: New title (optional)
            status_id: New status ID (optional)
            tags: New tags list (optional)
            due_date: New due date (optional)
        """
        data = {"version": version}
        if description is not None:
            data["description"] = description
        if subject is not None:
            data["subject"] = subject
        if status_id is not None:
            data["status"] = status_id
        if tags is not None:
            data["tags"] = tags
        if due_date is not None:
            data["due_date"] = due_date

        return await self._request("PATCH", f"/userstories/{story_id}", data=data)

    async def list_user_stories(
        self,
        project_id: int = None,
        status_id: int = None,
        tags: List[str] = None,
    ) -> List[Dict]:
        """List user stories from a project."""
        pid = project_id or await self.resolve_project_id()
        if not pid:
            return []
        params = {"project": pid}
        if status_id:
            params["status"] = status_id
        if tags:
            params["tags"] = ",".join(tags)

        try:
            stories = await self._request("GET", "/userstories", params=params)
            return stories or []
        except Exception as e:
            logger.error(f"Failed to list user stories: {e}")
            return []

    async def search_user_story_by_subject(self, subject: str, project_id: int = None) -> Optional[Dict]:
        """Search for a user story by subject (title)."""
        stories = await self.list_user_stories(project_id=project_id)
        for story in stories:
            if story.get("subject", "").strip().lower() == subject.strip().lower():
                return story
        return None

    def map_task_status_to_taiga(self, task_status: str, statuses: List[Dict]) -> Optional[int]:
        """Map internal task status to Taiga status ID."""
        # Default mapping - can be customized per project
        status_mapping = {
            "assigned": ["new", "ready", "to do", "backlog"],
            "in_progress": ["in progress", "doing", "started"],
            "on_hold": ["blocked", "on hold", "waiting"],
            "done": ["done", "closed", "completed", "finished"],
        }

        target_names = status_mapping.get(task_status, [])

        for taiga_status in statuses:
            status_name = taiga_status.get("name", "").lower()
            if status_name in target_names:
                return taiga_status.get("id")

        # Fallback: return first status if no match
        if statuses:
            return statuses[0].get("id")
        return None

    def map_taiga_status_to_task(self, taiga_status_name: str) -> str:
        """Map Taiga status name to internal task status."""
        status_name = taiga_status_name.lower()

        done_names = ["done", "closed", "completed", "finished", "archived"]
        in_progress_names = ["in progress", "doing", "started", "testing"]
        on_hold_names = ["blocked", "on hold", "waiting", "needs info"]

        if status_name in done_names:
            return "done"
        elif status_name in in_progress_names:
            return "in_progress"
        elif status_name in on_hold_names:
            return "on_hold"
        else:
            return "assigned"

    def extract_dates_from_story(self, taiga_story: Dict) -> Dict[str, Any]:
        """
        Extract and map dates from a Taiga user story to task date fields.

        Taiga user story date fields:
        - created_date: When the story was created
        - modified_date: When the story was last modified
        - due_date: Target completion date (maps to task.due_date)
        - finish_date: When the story was marked as done (maps to task.completed_date)

        For start_date, we use the created_date as a reasonable default.

        Returns:
            Dict with 'start_date', 'due_date', 'completed_date' keys (values can be None)
        """
        from datetime import datetime

        result = {
            "start_date": None,
            "due_date": None,
            "completed_date": None,
        }

        # Map due_date directly
        if taiga_story.get("due_date"):
            try:
                due_date_str = taiga_story["due_date"]
                # Handle both date-only and datetime formats
                if "T" in due_date_str:
                    result["due_date"] = datetime.fromisoformat(
                        due_date_str.replace("Z", "+00:00")
                    )
                else:
                    result["due_date"] = datetime.strptime(due_date_str, "%Y-%m-%d")
            except (ValueError, AttributeError) as e:
                logger.warning(f"Failed to parse due_date: {e}")

        # Map finish_date to completed_date
        if taiga_story.get("finish_date"):
            try:
                finish_date_str = taiga_story["finish_date"]
                if "T" in finish_date_str:
                    result["completed_date"] = datetime.fromisoformat(
                        finish_date_str.replace("Z", "+00:00")
                    )
                else:
                    result["completed_date"] = datetime.strptime(finish_date_str, "%Y-%m-%d")
            except (ValueError, AttributeError) as e:
                logger.warning(f"Failed to parse finish_date: {e}")

        # Use created_date as start_date (when work was assigned/created)
        if taiga_story.get("created_date"):
            try:
                created_date_str = taiga_story["created_date"]
                if "T" in created_date_str:
                    result["start_date"] = datetime.fromisoformat(
                        created_date_str.replace("Z", "+00:00")
                    )
                else:
                    result["start_date"] = datetime.strptime(created_date_str, "%Y-%m-%d")
            except (ValueError, AttributeError) as e:
                logger.warning(f"Failed to parse created_date: {e}")

        return result


# Singleton instance (uses settings by default)
taiga_client = TaigaClient()
