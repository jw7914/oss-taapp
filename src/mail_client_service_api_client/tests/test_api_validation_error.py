import pytest

from mail_client_service_api_client.models.validation_error import ValidationError


def test_to_dict_and_from_dict_roundtrip_and_extra_props() -> None:
    v = ValidationError(loc=[1, "field"], msg="must be present", type_="value_error")
    v["extra_num"] = 42
    v["extra_str"] = "z"

    d = v.to_dict()
    # required keys present
    assert d["loc"] == [1, "field"]
    assert d["msg"] == "must be present"
    assert d["type"] == "value_error"
    # extras preserved in dict
    assert d["extra_num"] == 42
    assert d["extra_str"] == "z"

    # round-trip via from_dict preserves extras
    v2 = ValidationError.from_dict(d)
    assert v2.loc == [1, "field"]
    assert v2.msg == "must be present"
    assert v2.type_ == "value_error"
    assert v2["extra_num"] == 42
    assert v2["extra_str"] == "z"
    assert set(v2.additional_keys) >= {"extra_num", "extra_str"}


def test_item_ops_and_contains_and_additional_keys_behavior() -> None:
    v = ValidationError(loc=[], msg="m", type_="t")
    assert v.additional_keys == []

    v["a"] = 1
    assert "a" in v
    assert v["a"] == 1
    assert v.additional_keys == ["a"]

    v["b"] = "two"
    # order of keys not guaranteed beyond insertion, check membership
    assert set(v.additional_keys) >= {"a", "b"}

    # delete and contains
    del v["a"]
    assert "a" not in v
    assert "b" in v

    # KeyError when accessing missing key
    with pytest.raises(KeyError):
        _ = v["missing_key"]
