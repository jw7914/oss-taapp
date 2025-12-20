"""Router for tasklist operations."""

import json
import logging
from typing import Annotated

from fastapi import APIRouter, Body, HTTPException
from task_client_api import TaskList as ServiceTaskList
from task_client_api import get_tasklist as get_service_tasklist

from task_client_service.dependencies import TaskClientDep

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasklists", tags=["tasklists"])


def tasklist_to_dict(tasklist: ServiceTaskList) -> dict[str, str]:
    """Convert a TaskList object to a JSON-serializable dictionary."""
    return {
        "id": tasklist.id,
        "title": tasklist.title,
        "etag": tasklist.etag,
        "updated": tasklist.updated,
        "self_link": tasklist.self_link,
    }


@router.get("")
async def list_tasklists(client: TaskClientDep) -> list[dict[str, str]]:
    """Get a list of tasklists from the task client."""
    logger.info("Received request to list tasklists")
    try:
        tasklists: list[ServiceTaskList] = client.list_tasklists()
        logger.info("Retrieved %d tasklists", len(tasklists))

    except Exception as e:
        logger.critical(e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e
    else:
        logger.info("Successfully formatted %d tasklists", len(tasklists))
        return [tasklist_to_dict(tasklist) for tasklist in tasklists]


@router.post("")
async def insert_tasklist(
    client: TaskClientDep,
    body: Annotated[
        dict[str, str],
        Body(
            examples=[
                {
                    "title": "My New Task List",
                },
            ],
        ),
    ],
) -> dict[str, str]:
    """Create a new tasklist."""
    title = body["title"]
    logger.info("Received request to insert tasklist with title: '%s'", title)
    try:
        new_tasklist = get_service_tasklist(json.dumps({"title": title}))

        new_tasklist = client.insert_tasklist(new_tasklist)
        logger.info("Successfully created tasklist with ID: %s", new_tasklist.id)
        return tasklist_to_dict(new_tasklist)
    except ValueError as e:
        logger.critical("Conflict: Tasklist with title '%s' already exists", title, exc_info=True)
        raise HTTPException(status_code=409, detail=str(e)) from e
    except Exception as e:
        logger.critical("Error inserting tasklist '%s': %s", title, e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/{tasklist_id}")
async def delete_tasklist(
    client: TaskClientDep,
    tasklist_id: str,
) -> dict[str, str]:
    """Delete a tasklist."""
    logger.info("Received request to delete tasklist with ID: '%s'", tasklist_id)

    tasklists: list[ServiceTaskList] = client.list_tasklists()

    # Reject deleting the default tasklist
    if tasklists and tasklists[0].id == tasklist_id:
        raise HTTPException(
            status_code=400,
            detail="Error: Invalid request cannot delete default tasklist",
        )

    # Find the target tasklist
    target_tasklist = next((t for t in tasklists if t.id == tasklist_id), None)

    if target_tasklist is None:
        raise HTTPException(status_code=404, detail=f"Error: Tasklist '{tasklist_id}' not found")

    try:
        success = client.delete_tasklist(tasklist_id)
    except Exception as e:  # unexpected failures from the client
        logger.exception("Error deleting tasklist '%s'", tasklist_id)
        raise HTTPException(status_code=500, detail="Internal error while deleting tasklist") from e
    else:
        if not success:
            raise HTTPException(
                status_code=500, detail=f"Failed to delete tasklist '{tasklist_id}'",
            )

        logger.info("Successfully deleted tasklist with ID: %s", tasklist_id)
        return {"detail": f"Tasklist '{target_tasklist.title}' deleted."}
