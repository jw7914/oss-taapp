from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from mail_client_api.message import Message

T = TypeVar("T", bound="MessageResponse")
X = TypeVar("X", bound="MessagesResponse")


@_attrs_define
class MessageResponse:
    """ """ 
    id: str
    from_: str
    to: str
    date: str
    subject: str
    body: str
    additional_properties: dict[str, str] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": self.id,
                "from_": self.from_,
                "to": self.to,
                "date": self.date,
                "subject": self.subject,
                "body": self.body,
            },
        )
        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        id = d.pop("id")
        from_ = d.pop("from_")
        to = d.pop("to")
        date = d.pop("date")
        subject = d.pop("subject")
        body = d.pop("body")

        message_response = cls(
            id=id,
            from_=from_,
            to=to,
            date=date,
            subject=subject,
            body=body,
        )

        message_response.additional_properties = d
        return message_response

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> str:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: str) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties


@_attrs_define
class MessagesResponse:
    """ """ 
    messages: list[dict[str,Any]]
    additional_properties: dict[str, str] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "messages": self.messages
            },
        )
        return field_dict

    @classmethod
    def from_dict(cls: type[X], src_dict: Mapping[str, Any]) -> X:
        d = dict(src_dict)
        messages = d.pop("messages")
        

        messages_response = cls(
            messages=messages
        )

        messages_response.additional_properties = d
        return messages_response 

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> str:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: str) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties

class MessageContents(Message):
    def __init__(self, response: MessageResponse):
        self.contents = response
    @property
    def id(self) -> str:
        return self.contents.id

    @property
    def from_(self) -> str:
        return self.contents.from_

    @property
    def to(self) -> str:
        return self.contents.to

    @property
    def date(self) -> str:
        return self.contents.date

    @property
    def subject(self) -> str:
        return self.contents.subject

    @property
    def body(self) -> str:
        return self.contents.body