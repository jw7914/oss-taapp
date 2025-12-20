"""Tests for explicit registration helpers exposed by ``gtask_client_impl``."""

import importlib

import pytest
import task_client_api
from task_client_api import task as task_protocol
from task_client_api import tasklist as tasklist_protocol

import gtask_client_impl


def test_register_binds_factories(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure calling register wires the client, task, and tasklist factories."""
    client_protocol = importlib.import_module("task_client_api.client")
    task_protocol_module = importlib.import_module("task_client_api.task")
    tasklist_protocol_module = importlib.import_module("task_client_api.tasklist")

    # Reset to protocol defaults before invoking register.
    monkeypatch.setattr(task_client_api, "get_client", client_protocol.get_client, raising=False)
    monkeypatch.setattr(
        task_protocol,
        "get_task",
        task_protocol_module.get_task,
        raising=False,
    )
    monkeypatch.setattr(
        task_client_api,
        "get_task",
        task_protocol_module.get_task,
        raising=False,
    )
    monkeypatch.setattr(
        tasklist_protocol,
        "get_tasklist",
        tasklist_protocol_module.get_tasklist,
        raising=False,
    )
    monkeypatch.setattr(
        task_client_api,
        "get_tasklist",
        tasklist_protocol_module.get_tasklist,
        raising=False,
    )

    gtask_client_impl.register()

    assert task_client_api.get_client is gtask_client_impl.get_client_impl
    assert task_protocol.get_task is gtask_client_impl.get_task_impl
    assert task_client_api.get_task is gtask_client_impl.get_task_impl
    assert tasklist_protocol.get_tasklist is gtask_client_impl.get_tasklist_impl
    assert task_client_api.get_tasklist is gtask_client_impl.get_tasklist_impl
