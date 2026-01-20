"""Google API client for Gmail, Calendar, and Docs integration."""
import logging
import base64
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.core.config import settings
from app.crud.google_token import google_token_db

logger = logging.getLogger(__name__)


class GoogleAPIClient:
    """Unified client for all Google API interactions."""

    SCOPES = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/calendar.events",
        "https://www.googleapis.com/auth/drive.readonly",
        "https://www.googleapis.com/auth/documents.readonly",
        "https://www.googleapis.com/auth/spreadsheets",  # Full access for read/write
    ]

    def __init__(self, user_id: int):
        self.user_id = user_id
        self._credentials: Optional[Credentials] = None

    def _get_credentials(self) -> Credentials:
        """Get valid credentials, refreshing if needed."""
        token_data = google_token_db.get_token(self.user_id)
        if not token_data:
            raise ValueError("No Google token found for user")

        creds = Credentials(
            token=token_data.access_token,
            refresh_token=token_data.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            scopes=token_data.scopes
        )

        # Refresh if expired
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                # Update stored token
                google_token_db.update_access_token(
                    self.user_id,
                    access_token=creds.token,
                    token_expiry=creds.expiry
                )
                logger.info(f"Refreshed Google token for user {self.user_id}")
            except Exception as e:
                logger.error(f"Failed to refresh token: {e}")
                raise

        return creds

    # ==================== GMAIL METHODS ====================

    def get_gmail_service(self):
        """Get Gmail API service."""
        creds = self._get_credentials()
        return build('gmail', 'v1', credentials=creds)

    def get_recent_emails(self, max_results: int = 50, query: str = None) -> List[Dict[str, Any]]:
        """
        Get recent emails from Gmail.

        Args:
            max_results: Maximum number of emails to fetch
            query: Gmail search query (e.g., "is:unread", "from:someone@example.com")

        Returns:
            List of email dictionaries with id, threadId, subject, sender, snippet, body_preview, received_at, labels
        """
        try:
            service = self.get_gmail_service()

            # Build query
            search_query = query or "in:inbox"

            # Get message list
            results = service.users().messages().list(
                userId='me',
                maxResults=max_results,
                q=search_query
            ).execute()

            messages = results.get('messages', [])
            emails = []

            for msg in messages:
                try:
                    # Get full message details
                    message = service.users().messages().get(
                        userId='me',
                        id=msg['id'],
                        format='full'
                    ).execute()

                    email_data = self._parse_email(message)
                    emails.append(email_data)
                except HttpError as e:
                    logger.warning(f"Failed to fetch email {msg['id']}: {e}")
                    continue

            logger.info(f"Fetched {len(emails)} emails for user {self.user_id}")
            return emails

        except HttpError as e:
            logger.error(f"Gmail API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching emails: {e}")
            raise

    def _parse_email(self, message: Dict) -> Dict[str, Any]:
        """Parse Gmail message into structured format."""
        headers = {h['name'].lower(): h['value'] for h in message.get('payload', {}).get('headers', [])}

        # Extract body preview
        body_preview = ""
        payload = message.get('payload', {})

        if 'body' in payload and payload['body'].get('data'):
            body_preview = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')
        elif 'parts' in payload:
            for part in payload['parts']:
                if part.get('mimeType') == 'text/plain' and part.get('body', {}).get('data'):
                    body_preview = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                    break

        # Truncate body preview
        body_preview = body_preview[:1000] if body_preview else ""

        # Parse date
        internal_date = message.get('internalDate')
        received_at = None
        if internal_date:
            received_at = datetime.fromtimestamp(int(internal_date) / 1000)

        return {
            'gmail_id': message['id'],
            'thread_id': message.get('threadId'),
            'subject': headers.get('subject', '(No Subject)'),
            'sender': headers.get('from', ''),
            'snippet': message.get('snippet', ''),
            'body_preview': body_preview,
            'received_at': received_at,
            'labels': message.get('labelIds', []),
        }

    # ==================== CALENDAR METHODS ====================

    def get_calendar_service(self):
        """Get Google Calendar API service."""
        creds = self._get_credentials()
        return build('calendar', 'v3', credentials=creds)

    def get_upcoming_events(self, days_ahead: int = 30, calendar_id: str = 'primary') -> List[Dict[str, Any]]:
        """
        Get upcoming calendar events.

        Args:
            days_ahead: Number of days to look ahead
            calendar_id: Calendar ID (default: 'primary')

        Returns:
            List of calendar event dictionaries
        """
        try:
            service = self.get_calendar_service()

            now = datetime.utcnow()
            time_min = now.isoformat() + 'Z'
            time_max = (now + timedelta(days=days_ahead)).isoformat() + 'Z'

            events_result = service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                maxResults=100,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])
            parsed_events = []

            for event in events:
                parsed_event = self._parse_calendar_event(event, calendar_id)
                parsed_events.append(parsed_event)

            logger.info(f"Fetched {len(parsed_events)} calendar events for user {self.user_id}")
            return parsed_events

        except HttpError as e:
            logger.error(f"Calendar API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching calendar events: {e}")
            raise

    def _parse_calendar_event(self, event: Dict, calendar_id: str) -> Dict[str, Any]:
        """Parse Google Calendar event into structured format."""
        # Handle all-day events vs timed events
        start = event.get('start', {})
        end = event.get('end', {})

        is_all_day = 'date' in start

        if is_all_day:
            start_time = datetime.strptime(start['date'], '%Y-%m-%d')
            end_time = datetime.strptime(end['date'], '%Y-%m-%d')
        else:
            start_time = datetime.fromisoformat(start.get('dateTime', '').replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(end.get('dateTime', '').replace('Z', '+00:00'))

        # Extract attendees
        attendees = []
        for attendee in event.get('attendees', []):
            attendees.append(attendee.get('email', ''))

        return {
            'event_id': event['id'],
            'calendar_id': calendar_id,
            'summary': event.get('summary', '(No Title)'),
            'description': event.get('description', ''),
            'location': event.get('location', ''),
            'start_time': start_time,
            'end_time': end_time,
            'attendees': attendees,
            'is_all_day': is_all_day,
            'status': event.get('status', 'confirmed'),
        }

    def create_calendar_event(
        self,
        summary: str,
        start_time: datetime,
        end_time: datetime,
        description: str = None,
        location: str = None,
        attendees: List[str] = None,
        calendar_id: str = 'primary'
    ) -> Dict[str, Any]:
        """
        Create a new calendar event.

        Returns:
            Created event data
        """
        try:
            service = self.get_calendar_service()

            event_body = {
                'summary': summary,
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': 'UTC',
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': 'UTC',
                },
            }

            if description:
                event_body['description'] = description
            if location:
                event_body['location'] = location
            if attendees:
                event_body['attendees'] = [{'email': email} for email in attendees]

            event = service.events().insert(
                calendarId=calendar_id,
                body=event_body,
                sendUpdates='all' if attendees else 'none'
            ).execute()

            logger.info(f"Created calendar event {event['id']} for user {self.user_id}")
            return event

        except HttpError as e:
            logger.error(f"Calendar API error creating event: {e}")
            raise

    # ==================== GOOGLE DOCS METHODS ====================

    def get_docs_service(self):
        """Get Google Docs API service."""
        creds = self._get_credentials()
        return build('docs', 'v1', credentials=creds)

    def get_drive_service(self):
        """Get Google Drive API service."""
        creds = self._get_credentials()
        return build('drive', 'v3', credentials=creds)

    def get_document_content(self, doc_id: str) -> Dict[str, Any]:
        """
        Get content of a Google Doc.

        Args:
            doc_id: Google Doc ID

        Returns:
            Dictionary with doc_id, title, content (plain text), last_modified
        """
        try:
            docs_service = self.get_docs_service()
            drive_service = self.get_drive_service()

            # Get document content
            document = docs_service.documents().get(documentId=doc_id).execute()

            # Get file metadata for last modified
            file_metadata = drive_service.files().get(
                fileId=doc_id,
                fields='modifiedTime,name,webViewLink'
            ).execute()

            # Extract plain text from document
            content = self._extract_doc_text(document)

            return {
                'doc_id': doc_id,
                'doc_name': document.get('title', file_metadata.get('name', 'Untitled')),
                'doc_url': file_metadata.get('webViewLink', f'https://docs.google.com/document/d/{doc_id}'),
                'content': content,
                'last_modified': datetime.fromisoformat(
                    file_metadata.get('modifiedTime', '').replace('Z', '+00:00')
                ) if file_metadata.get('modifiedTime') else None,
            }

        except HttpError as e:
            logger.error(f"Docs API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching document: {e}")
            raise

    def _extract_doc_text(self, document: Dict) -> str:
        """Extract plain text from Google Docs document structure."""
        text_parts = []

        content = document.get('body', {}).get('content', [])

        for element in content:
            if 'paragraph' in element:
                paragraph = element['paragraph']
                for elem in paragraph.get('elements', []):
                    if 'textRun' in elem:
                        text_parts.append(elem['textRun'].get('content', ''))
            elif 'table' in element:
                # Extract text from tables
                for row in element['table'].get('tableRows', []):
                    for cell in row.get('tableCells', []):
                        for cell_content in cell.get('content', []):
                            if 'paragraph' in cell_content:
                                for elem in cell_content['paragraph'].get('elements', []):
                                    if 'textRun' in elem:
                                        text_parts.append(elem['textRun'].get('content', ''))

        return ''.join(text_parts)

    def list_recent_documents(self, max_results: int = 20) -> List[Dict[str, Any]]:
        """
        List recent Google Docs the user has access to.

        Returns:
            List of document metadata
        """
        try:
            drive_service = self.get_drive_service()

            results = drive_service.files().list(
                q="mimeType='application/vnd.google-apps.document'",
                orderBy='modifiedTime desc',
                pageSize=max_results,
                fields='files(id, name, modifiedTime, webViewLink)'
            ).execute()

            files = results.get('files', [])
            documents = []

            for file in files:
                documents.append({
                    'doc_id': file['id'],
                    'doc_name': file.get('name', 'Untitled'),
                    'doc_url': file.get('webViewLink', f"https://docs.google.com/document/d/{file['id']}"),
                    'last_modified': datetime.fromisoformat(
                        file.get('modifiedTime', '').replace('Z', '+00:00')
                    ) if file.get('modifiedTime') else None,
                })

            logger.info(f"Listed {len(documents)} documents for user {self.user_id}")
            return documents

        except HttpError as e:
            logger.error(f"Drive API error: {e}")
            raise

    # ==================== GOOGLE SHEETS METHODS ====================

    def get_sheets_service(self):
        """Get Google Sheets API service."""
        creds = self._get_credentials()
        return build('sheets', 'v4', credentials=creds)

    def list_spreadsheets(self, max_results: int = 20) -> List[Dict[str, Any]]:
        """
        List recent Google Sheets the user has access to.

        Returns:
            List of spreadsheet metadata
        """
        try:
            drive_service = self.get_drive_service()

            results = drive_service.files().list(
                q="mimeType='application/vnd.google-apps.spreadsheet'",
                orderBy='modifiedTime desc',
                pageSize=max_results,
                fields='files(id, name, modifiedTime, webViewLink)'
            ).execute()

            files = results.get('files', [])
            spreadsheets = []

            for file in files:
                spreadsheets.append({
                    'spreadsheet_id': file['id'],
                    'name': file.get('name', 'Untitled'),
                    'url': file.get('webViewLink', f"https://docs.google.com/spreadsheets/d/{file['id']}"),
                    'last_modified': datetime.fromisoformat(
                        file.get('modifiedTime', '').replace('Z', '+00:00')
                    ) if file.get('modifiedTime') else None,
                })

            logger.info(f"Listed {len(spreadsheets)} spreadsheets for user {self.user_id}")
            return spreadsheets

        except HttpError as e:
            logger.error(f"Drive API error listing spreadsheets: {e}")
            raise

    def get_spreadsheet_info(self, spreadsheet_id: str) -> Dict[str, Any]:
        """
        Get spreadsheet metadata including sheet names.

        Args:
            spreadsheet_id: Google Spreadsheet ID

        Returns:
            Dictionary with spreadsheet info and list of sheets
        """
        try:
            sheets_service = self.get_sheets_service()

            spreadsheet = sheets_service.spreadsheets().get(
                spreadsheetId=spreadsheet_id,
                fields='spreadsheetId,properties.title,sheets.properties'
            ).execute()

            sheets = []
            for sheet in spreadsheet.get('sheets', []):
                props = sheet.get('properties', {})
                sheets.append({
                    'sheet_id': props.get('sheetId'),
                    'title': props.get('title'),
                    'index': props.get('index'),
                    'row_count': props.get('gridProperties', {}).get('rowCount', 0),
                    'column_count': props.get('gridProperties', {}).get('columnCount', 0),
                })

            return {
                'spreadsheet_id': spreadsheet.get('spreadsheetId'),
                'title': spreadsheet.get('properties', {}).get('title'),
                'sheets': sheets,
            }

        except HttpError as e:
            logger.error(f"Sheets API error: {e}")
            raise

    def get_sheet_headers(self, spreadsheet_id: str, sheet_name: str) -> List[str]:
        """
        Get the header row (first row) of a sheet.

        Args:
            spreadsheet_id: Google Spreadsheet ID
            sheet_name: Name of the sheet

        Returns:
            List of column headers
        """
        try:
            sheets_service = self.get_sheets_service()

            result = sheets_service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=f"'{sheet_name}'!1:1"
            ).execute()

            headers = result.get('values', [[]])[0]
            return headers

        except HttpError as e:
            logger.error(f"Sheets API error getting headers: {e}")
            raise

    def get_sheet_data(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        include_header: bool = True
    ) -> Dict[str, Any]:
        """
        Get all data from a sheet.

        Args:
            spreadsheet_id: Google Spreadsheet ID
            sheet_name: Name of the sheet
            include_header: Whether to include the header row

        Returns:
            Dictionary with headers and rows
        """
        try:
            sheets_service = self.get_sheets_service()

            result = sheets_service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=f"'{sheet_name}'"
            ).execute()

            values = result.get('values', [])

            if not values:
                return {'headers': [], 'rows': []}

            headers = values[0] if values else []
            rows = values[1:] if len(values) > 1 else []

            # Normalize rows to match header length
            normalized_rows = []
            for row in rows:
                # Pad row if shorter than headers
                while len(row) < len(headers):
                    row.append('')
                # Truncate row if longer than headers
                normalized_rows.append(row[:len(headers)])

            if include_header:
                return {
                    'headers': headers,
                    'rows': normalized_rows
                }
            else:
                return {
                    'headers': headers,
                    'rows': normalized_rows
                }

        except HttpError as e:
            logger.error(f"Sheets API error getting data: {e}")
            raise

    def get_sheet_rows_as_dicts(
        self,
        spreadsheet_id: str,
        sheet_name: str
    ) -> List[Dict[str, Any]]:
        """
        Get sheet data as a list of dictionaries (header: value).

        Args:
            spreadsheet_id: Google Spreadsheet ID
            sheet_name: Name of the sheet

        Returns:
            List of row dictionaries
        """
        data = self.get_sheet_data(spreadsheet_id, sheet_name)
        headers = data['headers']
        rows = data['rows']

        result = []
        for row in rows:
            row_dict = {}
            for i, header in enumerate(headers):
                row_dict[header] = row[i] if i < len(row) else ''
            result.append(row_dict)

        return result

    def append_sheet_rows(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        rows: List[List[Any]]
    ) -> Dict[str, Any]:
        """
        Append rows to a sheet.

        Args:
            spreadsheet_id: Google Spreadsheet ID
            sheet_name: Name of the sheet
            rows: List of rows (each row is a list of cell values)

        Returns:
            Dictionary with updated range info
        """
        try:
            sheets_service = self.get_sheets_service()

            body = {
                'values': rows
            }

            result = sheets_service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=f"'{sheet_name}'",
                valueInputOption='USER_ENTERED',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()

            logger.info(f"Appended {len(rows)} rows to {sheet_name}")
            return {
                'updated_range': result.get('updates', {}).get('updatedRange'),
                'updated_rows': result.get('updates', {}).get('updatedRows', 0)
            }

        except HttpError as e:
            logger.error(f"Sheets API error appending rows: {e}")
            raise

    def update_sheet_cell(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        cell_range: str,
        value: Any
    ) -> bool:
        """
        Update a single cell or range.

        Args:
            spreadsheet_id: Google Spreadsheet ID
            sheet_name: Name of the sheet
            cell_range: Cell reference (e.g., "A1", "B2:C3")
            value: Value to set (or list of lists for range)

        Returns:
            True if successful
        """
        try:
            sheets_service = self.get_sheets_service()

            # Wrap single value in nested list
            if not isinstance(value, list):
                values = [[value]]
            elif value and not isinstance(value[0], list):
                values = [value]
            else:
                values = value

            body = {'values': values}

            sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f"'{sheet_name}'!{cell_range}",
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()

            return True

        except HttpError as e:
            logger.error(f"Sheets API error updating cell: {e}")
            raise

    def update_sheet_row(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        row_number: int,
        values: List[Any],
        start_column: str = 'A'
    ) -> bool:
        """
        Update an entire row.

        Args:
            spreadsheet_id: Google Spreadsheet ID
            sheet_name: Name of the sheet
            row_number: Row number (1-indexed)
            values: List of values for the row
            start_column: Starting column letter (default 'A')

        Returns:
            True if successful
        """
        try:
            sheets_service = self.get_sheets_service()

            # Calculate end column
            end_col_index = ord(start_column.upper()) - ord('A') + len(values)
            end_column = chr(ord('A') + end_col_index - 1)

            cell_range = f"{start_column}{row_number}:{end_column}{row_number}"

            body = {'values': [values]}

            sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f"'{sheet_name}'!{cell_range}",
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()

            logger.info(f"Updated row {row_number} in {sheet_name}")
            return True

        except HttpError as e:
            logger.error(f"Sheets API error updating row: {e}")
            raise

    def find_row_by_value(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        column: str,
        value: str
    ) -> Optional[int]:
        """
        Find a row number by matching a value in a specific column.

        Args:
            spreadsheet_id: Google Spreadsheet ID
            sheet_name: Name of the sheet
            column: Column letter to search in
            value: Value to search for

        Returns:
            Row number (1-indexed) if found, None otherwise
        """
        try:
            sheets_service = self.get_sheets_service()

            result = sheets_service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=f"'{sheet_name}'!{column}:{column}"
            ).execute()

            values = result.get('values', [])

            for i, row in enumerate(values):
                if row and len(row) > 0 and str(row[0]).strip() == str(value).strip():
                    return i + 1  # 1-indexed

            return None

        except HttpError as e:
            logger.error(f"Sheets API error finding row: {e}")
            return None

    def batch_update_sheet(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        updates: List[Dict[str, Any]]
    ) -> int:
        """
        Batch update multiple cells/ranges efficiently.

        Args:
            spreadsheet_id: Google Spreadsheet ID
            sheet_name: Name of the sheet
            updates: List of updates, each with 'range' and 'values' keys

        Returns:
            Number of cells updated
        """
        try:
            sheets_service = self.get_sheets_service()

            data = []
            for update in updates:
                data.append({
                    'range': f"'{sheet_name}'!{update['range']}",
                    'values': update['values'] if isinstance(update['values'][0], list)
                              else [update['values']]
                })

            body = {
                'valueInputOption': 'USER_ENTERED',
                'data': data
            }

            result = sheets_service.spreadsheets().values().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=body
            ).execute()

            total_updated = result.get('totalUpdatedCells', 0)
            logger.info(f"Batch updated {total_updated} cells in {sheet_name}")
            return total_updated

        except HttpError as e:
            logger.error(f"Sheets API error batch updating: {e}")
            raise
