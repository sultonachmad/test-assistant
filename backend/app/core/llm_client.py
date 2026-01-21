"""LLM Client for interacting with the LLM Gateway."""
import logging
import json
from typing import List, Dict, Any, Optional
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMClient:
    """Client for making calls to the LLM gateway."""

    def __init__(self):
        self.base_url = settings.LLM_GATEWAY_URL
        self.api_key = settings.LLM_GATEWAY_KEY
        self.model = settings.LLM_MODEL
        self.summary_model = settings.LLM_MODEL_SUMMARY

    async def _call_llm(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        """Make a call to the LLM gateway."""
        model = model or self.model

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    },
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
            except httpx.HTTPStatusError as e:
                logger.error(f"LLM API error: {e.response.status_code} - {e.response.text}")
                raise
            except Exception as e:
                logger.error(f"LLM call failed: {e}")
                raise

    async def summarize_emails(self, emails: List[Dict[str, Any]]) -> str:
        """Generate a summary of multiple emails."""
        if not emails:
            return "No emails to summarize."

        email_texts = []
        for i, email in enumerate(emails, 1):
            email_text = f"""
Email {i}:
- From: {email.get('sender', 'Unknown')}
- Subject: {email.get('subject', 'No Subject')}
- Date: {email.get('received_at', 'Unknown')}
- Preview: {email.get('snippet', email.get('body_preview', 'No content'))[:500]}
"""
            email_texts.append(email_text)

        prompt = f"""Please provide a concise summary of the following {len(emails)} emails.
Highlight key topics, important requests, deadlines mentioned, and any action items.

{chr(10).join(email_texts)}

Summary:"""

        messages = [
            {"role": "system", "content": "You are a helpful assistant that summarizes emails concisely and identifies key action items."},
            {"role": "user", "content": prompt}
        ]

        return await self._call_llm(messages, model=self.summary_model, temperature=0.3)

    async def extract_task_suggestions(self, emails: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract task suggestions from emails using AI."""
        if not emails:
            return []

        email_texts = []
        for i, email in enumerate(emails, 1):
            email_text = f"""
Email {i} (ID: {email.get('gmail_id', email.get('id', i))}):
- From: {email.get('sender', 'Unknown')}
- Subject: {email.get('subject', 'No Subject')}
- Date: {email.get('received_at', 'Unknown')}
- Content: {email.get('snippet', email.get('body_preview', 'No content'))[:800]}
"""
            email_texts.append(email_text)

        prompt = f"""Analyze the following emails and extract potential tasks or action items.
For each task found, provide:
- title: A clear, actionable task title
- description: Brief context about the task
- priority: low, medium, high, or urgent (based on urgency indicators)
- source_email_index: The email number (1-based) this task came from
- due_date_hint: Any mentioned deadline or "none" if not specified

Return ONLY a valid JSON array of task objects. If no tasks found, return empty array [].

Emails:
{chr(10).join(email_texts)}

Return JSON array:"""

        messages = [
            {"role": "system", "content": """You are a task extraction assistant. Your job is to identify actionable tasks from emails.
Look for: requests, deadlines, meetings to schedule, items to review, follow-ups needed, approvals required.
Return ONLY valid JSON array, no other text."""},
            {"role": "user", "content": prompt}
        ]

        try:
            result = await self._call_llm(messages, temperature=0.2, max_tokens=3000)

            # Clean up the response - remove markdown code blocks if present
            result = result.strip()
            if result.startswith("```json"):
                result = result[7:]
            if result.startswith("```"):
                result = result[3:]
            if result.endswith("```"):
                result = result[:-3]
            result = result.strip()

            tasks = json.loads(result)

            # Enrich tasks with email source info
            for task in tasks:
                idx = task.get("source_email_index", 1) - 1
                if 0 <= idx < len(emails):
                    email = emails[idx]
                    task["source_email_id"] = email.get("gmail_id", email.get("id"))
                    task["source_email_subject"] = email.get("subject", "Unknown")
                    task["source_email_sender"] = email.get("sender", "Unknown")

            return tasks
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.error(f"Raw response: {result}")
            return []
        except Exception as e:
            logger.error(f"Task extraction failed: {e}")
            return []

    async def generate_task_description(
        self,
        title: str,
        current_description: Optional[str] = None,
        project: Optional[str] = None,
    ) -> Dict[str, str]:
        """Generate a good task description and title suggestion based on task title and context.

        Returns:
            Dict with 'description' and 'suggested_title' keys.
        """
        context_parts = []
        if project:
            context_parts.append(f"Project: {project}")
        if current_description:
            context_parts.append(f"Current description: {current_description}")

        context = "\n".join(context_parts) if context_parts else "No additional context"

        prompt = f"""Generate a clear, professional task description and an improved title suggestion for the following task.

Task title: {title}
{context}

Requirements:
1. Description must be in **Markdown format** with proper formatting:
   - Use bullet points for lists of items or acceptance criteria
   - Use **bold** for emphasis on key terms
   - Use headers (##, ###) if the description is longer
   - Include acceptance criteria as a checklist if applicable (- [ ] item)
   - Be concise but informative (2-5 sentences or bullet points)
   - Be actionable and specific
2. Suggested title should be an improved, clearer version of the original title - make it more specific and actionable.

Return ONLY valid JSON in this exact format:
{{"suggested_title": "improved title here", "description": "markdown description here"}}"""

        messages = [
            {"role": "system", "content": "You are a helpful assistant that writes clear, professional task descriptions and titles for project management. Always format descriptions in Markdown. Always return valid JSON only."},
            {"role": "user", "content": prompt}
        ]

        try:
            result = await self._call_llm(messages, model=self.summary_model, temperature=0.5, max_tokens=500)

            # Clean up the response - remove markdown code blocks if present
            result = result.strip()
            if result.startswith("```json"):
                result = result[7:]
            if result.startswith("```"):
                result = result[3:]
            if result.endswith("```"):
                result = result[:-3]
            result = result.strip()

            parsed = json.loads(result)
            return {
                "suggested_title": parsed.get("suggested_title", ""),
                "description": parsed.get("description", "")
            }
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}. Raw: {result}")
            # Fallback: treat entire response as description
            return {
                "suggested_title": "",
                "description": result
            }

    async def generate_task_comment(
        self,
        task,
        comment_type: str,
        user_prompt: Optional[str] = None,
        context_comments: Optional[List] = None
    ) -> Dict[str, Any]:
        """Generate an AI comment for a task.

        Args:
            task: The task object
            comment_type: One of 'ask', 'update', 'solution', 'test_case'
            user_prompt: Optional user prompt for additional context
            context_comments: Optional list of selected comments for context

        Returns:
            Dict with 'content' and optionally 'estimated_days', 'suggested_start_date', 'suggested_due_date'
        """
        from datetime import datetime, timedelta

        # Build task context
        task_context = f"""Task Information:
- Title: {task.title}
- Description: {task.description or 'No description'}
- Status: {task.status}
- Priority: {task.priority}
- Project: {task.project or 'Not specified'}
- Assigned to: {task.assigned_to or 'Not assigned'}
- Start date: {task.start_date.strftime('%Y-%m-%d') if task.start_date else 'Not set'}
- Due date: {task.due_date.strftime('%Y-%m-%d') if task.due_date else 'Not set'}"""

        # Build comments context
        comments_context = ""
        if context_comments:
            comments_text = []
            for c in context_comments:
                comments_text.append(f"[{c.comment_type.upper()}] {c.content}")
            comments_context = f"\n\nSelected Comments for Context:\n" + "\n---\n".join(comments_text)

        # Build type-specific prompt
        type_prompts = {
            "ask": """Generate a clarifying question to gather more information about this task.
The question should help understand requirements, scope, or missing details.
Format: Write a clear, professional question in Markdown format.""",

            "update": """Generate a progress update comment for this task.
The update should describe potential progress, blockers, or status changes.
Format: Write a concise progress update in Markdown format with bullet points if needed.""",

            "solution": """Generate a solution comment that:
1. Analyzes the task and identifies the approach or root cause
2. Proposes a solution or implementation plan
3. Estimates the effort in working days (mandays)

You MUST return valid JSON with these fields:
{
  "content": "Your markdown solution content here",
  "estimated_days": <number of working days as integer>
}""",

            "test_case": """Generate test cases or completion criteria for this task.
Include:
- Test scenarios to verify the task is complete
- Acceptance criteria checklist
- Edge cases to consider

Format: Write in Markdown format with checkboxes (- [ ] item) for each test case."""
        }

        prompt = f"""{task_context}{comments_context}

{user_prompt or ''}

{type_prompts.get(comment_type, type_prompts['update'])}"""

        messages = [
            {"role": "system", "content": "You are a helpful project management assistant that writes clear, professional task comments. Always provide actionable and specific content."},
            {"role": "user", "content": prompt}
        ]

        try:
            result = await self._call_llm(messages, model=self.summary_model, temperature=0.5, max_tokens=1000)
            result = result.strip()

            # For solution type, parse JSON response
            if comment_type == "solution":
                # Clean up response
                if result.startswith("```json"):
                    result = result[7:]
                if result.startswith("```"):
                    result = result[3:]
                if result.endswith("```"):
                    result = result[:-3]
                result = result.strip()

                try:
                    parsed = json.loads(result)
                    content = parsed.get("content", result)
                    estimated_days = parsed.get("estimated_days", 1)

                    # Calculate suggested dates
                    start_date = task.start_date or datetime.utcnow()
                    if isinstance(start_date, str):
                        start_date = datetime.fromisoformat(start_date.replace("Z", "+00:00"))

                    # Due date = start_date + estimated_days + 1 (buffer)
                    due_date = start_date + timedelta(days=estimated_days + 1)

                    return {
                        "content": content,
                        "estimated_days": estimated_days,
                        "suggested_start_date": start_date,
                        "suggested_due_date": due_date
                    }
                except json.JSONDecodeError:
                    # Fallback: use content as-is with default estimation
                    return {
                        "content": result,
                        "estimated_days": 1,
                        "suggested_start_date": task.start_date or datetime.utcnow(),
                        "suggested_due_date": (task.start_date or datetime.utcnow()) + timedelta(days=2)
                    }
            else:
                return {"content": result}

        except Exception as e:
            logger.error(f"Error generating task comment: {e}")
            raise

    async def suggest_tasks_from_comments(
        self,
        task,
        comments: List,
        user_prompt: Optional[str] = None
    ) -> List[Dict]:
        """Generate task suggestions from selected comments (like email suggestion).

        Args:
            task: The parent task object
            comments: List of selected comments for context
            user_prompt: Optional user prompt for additional context

        Returns:
            List of task suggestion dicts
        """
        # Build task context
        task_context = f"""Parent Task:
- Title: {task.title}
- Description: {task.description or 'No description'}
- Project: {task.project or 'Not specified'}"""

        # Build comments context
        comments_text = []
        for c in comments:
            comments_text.append(f"[{c.comment_type.upper()}]\n{c.content}")
        comments_context = "\n\n---\n\n".join(comments_text)

        prompt = f"""{task_context}

Selected Comments:
{comments_context}

{user_prompt or ''}

Based on the task and selected comments above, generate sub-tasks or follow-up tasks.
Each task should be specific, actionable, and derived from the comments.

Return ONLY valid JSON array with this format:
[
  {{
    "title": "Task title",
    "description": "Task description in Markdown",
    "priority": "low|medium|high|urgent",
    "estimated_days": <number>
  }}
]

Generate 1-5 relevant tasks based on the content."""

        messages = [
            {"role": "system", "content": "You are a helpful project management assistant that creates actionable sub-tasks from discussion comments. Always return valid JSON array."},
            {"role": "user", "content": prompt}
        ]

        try:
            result = await self._call_llm(messages, model=self.summary_model, temperature=0.5, max_tokens=1500)
            result = result.strip()

            # Clean up response
            if result.startswith("```json"):
                result = result[7:]
            if result.startswith("```"):
                result = result[3:]
            if result.endswith("```"):
                result = result[:-3]
            result = result.strip()

            suggestions = json.loads(result)
            if not isinstance(suggestions, list):
                suggestions = [suggestions]

            return suggestions

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse task suggestions: {e}")
            return []
        except Exception as e:
            logger.error(f"Error generating task suggestions: {e}")
            raise


# Singleton instance
llm_client = LLMClient()
