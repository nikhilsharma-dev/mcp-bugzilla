# server.py
from fastmcp import FastMCP
import requests
from typing import Dict, Any
import logging
import os

# Configure logging
logging.basicConfig(filename='bugzilla_mcp.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# constants for Bugzilla API
BUGZILLA_API_URL = os.getenv("BUGZILLA_API_URL")
if not BUGZILLA_API_URL:
    logger.error("BUGZILLA_API_URL environment variable is not set.")
    raise ValueError("BUGZILLA_API_URL environment variable is required.")
BUGZILLA_API_KEY = os.getenv("BUGZILLA_API_KEY")
if not BUGZILLA_API_KEY:
    logger.error("BUGZILLA_API_KEY environment variable is not set.")
    raise ValueError("BUGZILLA_API_KEY environment variable is required.")
PORT = 4200
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
}
# Create an MCP server
mcp = FastMCP("Bugzilla MCP Server", "1.0.0")

# Get Bug details from bugzilla
# GET /rest/bug?id=12434,43421
@mcp.tool()
def get_bug(bug_ids: str) -> Dict[str, Any]:
    """
    Gets details about particular bugs in Bugzilla.

    Args:
        bug_ids (str): single ID of the bug to fetch or multiple bugs with IDs separated by commas.
    Returns:
        dict: {
        "faults": [],
        "bugs": [dict[str, Any],...]
        }
    Raises:
        Exception: If the Bugzilla Request fails.
    Example:
        ```python
        # Get a bug with ID 123456
        get_bug("123456")

        # Get multiple bugs with IDs 123456, 789012
        get_bug("123456,789012")
        ```
    """
    url = f"{BUGZILLA_API_URL}bug"
    params = {"id": bug_ids, "api_key": BUGZILLA_API_KEY}
    response = requests.get(
        url,
        params=params,
        verify=False,
        headers=HEADERS
    )
    if response.status_code != 200:
        if response.status_code == 404:
            logger.error(f" Bug not found: {bug_ids}")
            return {"error": "Bug not found"}
        logger.error(f"Bugzilla response status: {response.status_code}")
        logger.error(f"Bugzilla response text: {response.text}")
        raise ValueError("Failed to fetch Bugzilla bug details.")
    return response.json()

# Get Bugs history
# GET /rest/bug/(id)/history?new_since=YYYY-MM-DD
@mcp.tool()
def get_bug_history(bug_id: str, new_since: str = "1970-01-01") -> Dict[str, Any]:
    """
    Gets the history of a particular bug in Bugzilla.
    Args:
        bug_id (str): ID of the bug to fetch history for.
        new_since (str) (optional): Date in YYYY-MM-DD format to filter history changes.
    Returns:
        bugs (list of dict): Each bug object contains the following fields:
        - id (int): The numeric ID of the bug.
        - alias (list of str): Unique aliases for this bug. Empty if no aliases exist.
        - history (list of dict): List of history objects, each representing a change event for the bug.
        
        History object fields:
            - when (datetime): The date and time when the bug activity/change occurred.
            - who (str): The login name of the user who performed the change.
            - changes (list of dict): List of change objects, each describing a specific field change.
            
            Change object fields:
                - field_name (str): The name of the bug field that was changed.
                - removed (str): The previous value of the field that was removed.
                - added (str): The new value of the field that was added.
                - attachment_id (int, optional): The ID of the attachment that was changed (present only for attachment changes). 
    Raises:
        ValueError: If the Bugzilla Request fails.
    Example:
        ```python
        # Get history of a bug with ID 123456
        get_bug_history("123456")
        # Get history of a bug with ID 123456 since 2023-01-01
        get_bug_history("123456", "2023-01-01")
        ```
    """
    url = f"{BUGZILLA_API_URL}bug/{bug_id}/history"
    params = {"new_since": new_since, "api_key": BUGZILLA_API_KEY}
    response = requests.get(
        url,
        params=params,
        verify=False,
        headers=HEADERS
    )
    if response.status_code != 200:
        if response.status_code == 404:
            logger.error(f" Bug not found: {bug_id}")
            return {"error": "Bug not found"}
        logger.error(f"Bugzilla response status: {response.status_code}")
        logger.error(f"Bugzilla response text: {response.text}")
        raise ValueError("Failed to fetch Bugzilla bug history.")
    return response.json()

# Search Bugs
# GET /rest/bug?alias=alias1
@mcp.tool()
def search_bugs(query_strs: Dict[str, str]) -> Dict[str, Any]:
    """
    Searches for bugs in Bugzilla based on the provided query parameters.
    
    Args:
        query_strs (dict): Dictionary containing search parameters.
        Valid keys include:
            alias (list of str): Unique aliases for the bug. An empty list if no aliases exist.
        assigned_to (str): Login name of the user the bug is assigned to.
        component (str): Name of the Component the bug is in. If multiple components share the same name, all are matched unless 'product' is also specified.
        creation_time (datetime): Only return bugs created at this time or later.
        creator (str): Login name of the user who created the bug. Also accepts 'reporter' for compatibility.
        id (int): Numeric ID of the bug.
        last_change_time (datetime): Only return bugs modified at this time or later.
        limit (int): Maximum number of results to return. If set to zero, all matching results are returned.
        offset (int): Starting position for the search results (used with 'limit' for pagination).
        op_sys (str): Value of the "Operating System" field.
        platform (str): Value of the "Platform" (hardware) field.
        priority (str): Value of the "Priority" field.
        product (str): Name of the Product the bug is in.
        resolution (str): Current resolution of the bug (only set if bug is closed). To find open bugs, search for an empty resolution.
        severity (str): Value of the "Severity" field.
        status (str): Current status of the bug (not including resolution).
        summary (str or list of str): Substring(s) to search for in the bug's summary. If a list is provided, matches any of the substrings.
        tags (str or list of str): Tag(s) to search for. If a list is provided, matches any of the tags. Tags are personal to the logged-in user.
        target_milestone (str): Value of the "Target Milestone" field.
        qa_contact (str): Login name of the bug's QA Contact.
        url (str): Value of the "URL" field.
        version (str): Value of the "Version" field.
        whiteboard (str): Substring to search for in the "Status Whiteboard" field. Behaves like 'summary'.
        quicksearch (str): Query string using Bugzilla's quicksearch syntax.

    Notes:
        - Unless otherwise specified, all parameters require exact matches.
        - Multiple values for a parameter (where allowed) are treated as logical OR for that field.
        - All parameters are combined using logical AND.
        - Some fields (e.g., summary, whiteboard, tags) support substring or array-based matching as described above.
        - When no 'product' is specified, bugs from all products are included in the search.
        
    Returns:
        dict: Search results containing a list of bugs and any faults.
        
    Raises:
        ValueError: If the Bugzilla Request fails.
        
    Example:
        ```python
        # Search for bugs with a specific status
        search_bugs({"status": "NEW"})
        ```
    """
    url = f"{BUGZILLA_API_URL}bug"
    params = {"api_key": BUGZILLA_API_KEY, **query_strs}
    response = requests.get(
        url,
        params=params,
        verify=False,
        headers=HEADERS
    )
    if response.status_code != 200:
        logger.error(f"Bugzilla response status: {response.status_code}")
        logger.error(f"Bugzilla response text: {response.text}")
        raise ValueError("Failed to search Bugzilla bugs.")
    return response.json()

# create a new bug
# POST /rest/bug
@mcp.tool()
def create_bug(bug_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Creates a new bug in Bugzilla.
    
    Create Bug Parameters (Bugzilla REST API)

    Args:
        product (str): **Required.** Name of the product the bug is being filed against.
        component (str): **Required.** Name of a component in the specified product.
        summary (str): **Required.** Brief description of the bug.
        version (str): **Required.** Version of the product where the bug was found.
        description (str): (Defaulted) Initial description for this bug. Some Bugzilla installations require this to not be blank.
        op_sys (str): (Defaulted) Operating system where the bug was discovered.
        platform (str): (Defaulted) Hardware type where the bug was experienced.
        priority (str): (Defaulted) Priority for fixing this bug.
        severity (str): (Defaulted) Severity of the bug.
        alias (list of str): One or more unique aliases for the bug.
        assigned_to (str): User to assign the bug to (optional; defaults to component owner if not set).
        cc (list of str): Usernames to CC on this bug.
        comment_is_private (bool): If True, the description is private; otherwise, it is public.
        groups (list of str): Group names to add this bug to. If omitted, bug is added to all default groups for the product.
        qa_contact (str): QA Contact for the bug (if enabled).
        status (str): Status for the new bug (only certain statuses allowed at creation).
        resolution (str): Resolution if filing a closed bug (cannot use DUPLICATE at creation).
        target_milestone (str): Target milestone for this product.
        flags (list of dict): Flags to add to the bug. Each flag object must include at least 'status' and either 'type_id' or 'name'. Optionally, 'requestee' may be set.
            Flag object fields:
                - name (str): Name of the flag type.
                - type_id (int): Internal flag type ID.
                - status (str): Flag status ("?", "+", "-", or "X" to clear).
                - requestee (str): Login of the requestee (if applicable).

        Any custom fields for your Bugzilla installation can also be set by passing the field name and its value as a string.

    Notes:
        - Parameters marked **Required** must always be set, or an error will be thrown.
        - Parameters marked (Defaulted) may be omitted if the Bugzilla administrator has set a default; otherwise, they must be specified to avoid errors.
        - For compatibility across multiple Bugzilla instances, always set both **Required** and (Defaulted) parameters.

    Returns:
        dict: {
            "id": int  # The ID of the newly-filed bug.
        }

    Raises:
        ValueError: If the Bugzilla Request fails.
        
    Example:
        ```python
        # Create a new bug
        create_bug({
            "product": "MyProduct",
            "component": "MyComponent",
            "summary": "Bug summary",
            "description": "Detailed description of the bug",
            "version": "1.0",
            "severity": "normal"
        })
        ```
    """
    url = f"{BUGZILLA_API_URL}bug"
    params = {"api_key": BUGZILLA_API_KEY}
    response = requests.post(
        url,
        json=bug_data,
        params=params,
        verify=False,
        headers=HEADERS
    )
    if response.status_code != 201:
        logger.error(f"Bugzilla response status: {response.status_code}")
        logger.error(f"Bugzilla response text: {response.text}")
        raise ValueError("Failed to create Bugzilla bug.")
    return response.json()

# Update existing bug
# PUT /rest/bug/(id)
@mcp.tool()
def update_bug(bug_id: str, bug_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update Bug Parameters 

    Args:
        id_or_alias (int or str): Bug ID or alias to update (can be specified in URL or in 'ids').
        ids (list of int or str): List of bug IDs or aliases to update. Can be combined with id_or_alias for batch updates.

        # Fields to update (all optional; only include those you wish to modify):

        alias (dict or str): Aliases for the bug. Pass a dict with:
            - add (list of str): Aliases to add.
            - remove (list of str): Aliases to remove.
            - set (list of str): Exact set of aliases to use (overrides add/remove).
            If a single string is given, it is treated as set.
            Note: Only allowed when updating a single bug.

        assigned_to (str): Login name of the user to assign the bug to.
        blocks (dict): Bugs blocked by this bug. Dict with 'add', 'remove', or 'set' (lists of bug IDs).
        depends_on (dict): Bugs this bug depends on. Dict with 'add', 'remove', or 'set' (lists of bug IDs).
        cc (dict): CC list modifications. Dict with:
            - add (list of str): Usernames to add to CC.
            - remove (list of str): Usernames to remove from CC.
        is_cc_accessible (bool): Whether users in CC can access the bug.
        comment (dict): Add a comment to the bug. Dict with:
            - body (str): Comment text (or 'comment' as an alias).
            - is_private (bool): If True, comment is private.
        comment_is_private (dict): Update privacy of existing comments. Dict mapping comment IDs (int) to bool (True=private, False=public).
        component (str): Component name.
        deadline (str): Deadline date (YYYY-MM-DD).
        dupe_of (int): ID of the bug this is a duplicate of.
        estimated_time (float): Total estimated time (in hours) to fix the bug.
        flags (list of dict): List of flag change objects. Each object may include:
            - name (str): Flag name.
            - type_id (int): Internal flag type ID.
            - status (str): Flag status ("?", "+", "-", "X").
            - requestee (str): Login of the requestee (if applicable).
            - id (int): ID of the flag to update.
            - new (bool): Set True to create a new flag.
        groups (dict): Group modifications. Dict with:
            - add (list of str): Groups to add.
            - remove (list of str): Groups to remove.
        keywords (dict): Keyword modifications. Dict with:
            - add (list of str): Keywords to add.
            - remove (list of str): Keywords to remove.
            - set (list of str): Exact set of keywords (overrides add/remove).
        op_sys (str): Operating system value.
        platform (str): Hardware/platform value.
        priority (str): Priority value.
        product (str): Product name. If changed, you may also need to update target_milestone, version, and component.
        qa_contact (str): QA contact's login name.
        is_creator_accessible (bool): Whether the bug's reporter can access the bug.
        remaining_time (float): Remaining work time (in hours).
        reset_assigned_to (bool): If True, resets assigned_to to the component default.
        reset_qa_contact (bool): If True, resets qa_contact to the component default.
        resolution (str): Resolution value (only for closing or already-closed bugs).
        see_also (dict): URLs to other bug trackers. Dict with:
            - add (list of str): URLs to add.
            - remove (list of str): URLs to remove.
        severity (str): Severity value.
        status (str): Status to change the bug to. If moving to closed, specify resolution.
        summary (str): Summary/short description.
        target_milestone (str): Target milestone value.
        url (str): URL field value.
        version (str): Version value.
        whiteboard (str): Status whiteboard value.
        work_time (float): Hours worked as part of this change.

        # Custom fields:
        Any custom field can be set by passing its name and value. For multi-select fields, use a list of strings.

    Returns:
        dict: {
            "bugs": [
                {
                    "id": int,                    # ID of the updated bug
                    "alias": list of str,         # Aliases for the bug
                    "last_change_time": str,      # Time of this update (ISO 8601 format)
                    "changes": dict {             # Fields actually changed
                        "<field_name>": {
                            "added": str,         # Values added (comma-separated if multiple)
                            "removed": str        # Values removed (comma-separated if multiple)
                        },
                        ...
                    }
                },
                ...
            ]
        }

    Notes:
        - Some fields (comment, comment_is_private, work_time) may not appear in 'changes' even if updated.
        - You can update multiple bugs at once using 'ids'.
        - For fields that accept objects (e.g., alias, cc, depends_on), specifying 'set' overrides 'add' and 'remove'.
        - If you change a bug's product, related fields (target_milestone, version, component, groups) may also need to be updated.
        - Only users with appropriate permissions can update certain fields or move bugs between products.
    Raises:
        ValueError: If the Bugzilla Request fails.
    Example:
        ```python
        # Update a bug with ID 123456
        update_bug("123456", {
            "summary": "Updated summary",
            "status": "RESOLVED",
            "resolution": "FIXED",
            "comment": {
                "body": "This bug has been fixed.",
                "is_private": False
            }
        })
        ```
    """
    url = f"{BUGZILLA_API_URL}bug/{bug_id}"
    params = {"api_key": BUGZILLA_API_KEY}
    response = requests.put(
        url,
        json=bug_data,
        params=params,
        verify=False,
        headers=HEADERS
    )
    if response.status_code != 200:
        logger.error(f"Bugzilla response status: {response.status_code}")
        logger.error(f"Bugzilla response text: {response.text}")
        raise ValueError("Failed to update Bugzilla bug.")
    return response.json()

# Get bug comments, which includes the initial description of the bug.
# GET /rest/bug/(id)/comment
@mcp.tool()
def get_bug_comments(bug_id: str) -> Dict[str, Any]:
    """
    Gets comments for a specific bug in Bugzilla. 
    Typically first comment is the initial description of the bug.
    first comment may also contain the reproduction steps, if provided.
    Any subsequent comment numbers are the comments users have left for the bug.


    Args:
        bug_id (str): ID of the bug to fetch comments for.
    
    Returns:
        dict: {
        "bugs": {
        {id}: {
        'comments': dict[str, Any],  # Comments for the bug
        }}}
        Response format:
            {
        "bugs": {
            "35": {
            "comments": [
                {
                "time": "2000-07-25T13:50:04Z",
                "text": "test bug to fix problem in removing from cc list.",
                "bug_id": 35,
                "count": 0,
                "attachment_id": null,
                "is_private": false,
                "tags": [],
                "creator": "user@bugzilla.org",
                "creation_time": "2000-07-25T13:50:04Z",
                "id": 75
                }
            ]
            }
            },
            "comments": {}
        }
        A Bugzilla comment object.

        Attributes:
        id (int): The globally unique ID for the comment.

        bug_id (int): The ID of the bug that this comment is on.

        attachment_id (int or None): If the comment was made on an attachment, this
            will be the ID of that attachment. Otherwise, it will be None.

        count (int): The number of the comment local to the bug.
            The Description is 0; comments start with 1.

        text (str): The actual text of the comment.

        creator (str): The login name of the comment’s author.

        time (datetime): The time (in Bugzilla’s timezone) that the comment was added.

        creation_time (datetime): Same as the `time` field. Use this field instead of
            `time` for consistency with other methods, including Get Bug and Get Attachment.
            For compatibility, `time` is still usable but may be deprecated in a future release.

        is_private (bool): True if this comment is private (only visible to a certain
            group called the “insidergroup”), False otherwise.
    
    Raises:
        ValueError: If the Bugzilla Request fails.
    
    Example:
        ```python
        # Get comments for a bug with ID 123456
        get_bug_comments("123456")
        ```
    """
    url = f"{BUGZILLA_API_URL}bug/{bug_id}/comment"
    params = {"api_key": BUGZILLA_API_KEY}
    response = requests.get(
        url,
        params=params,
        verify=False,
        headers=HEADERS
    )
    if response.status_code != 200:
        if response.status_code == 404:
            logger.error(f" Bug not found: {bug_id}")
            return {"error": "Bug not found"}
        logger.error(f"Bugzilla response status: {response.status_code}")
        logger.error(f"Bugzilla response text: {response.text}")
        raise ValueError("Failed to fetch Bugzilla bug comments.")
    return response.json()

if __name__ == "__main__":
    mcp.run(transport="http",
        host="127.0.0.1",
        port=PORT,
        path="/mcp",
        log_level="debug",
    )