import os
import pytest
from dbdb.interface import connect
from dbdb.tool import main


@pytest.fixture
def temp_db_path(tmp_path):
    return str(tmp_path / "test.db")


def test_basic_key_value_operations(temp_db_path):
    db = connect(temp_db_path)
    db["alpha"] = "1"
    db["beta"] = "2"
    db["gamma"] = "3"
    db.commit()
    db.close()

    db_reopened = connect(temp_db_path)
    assert db_reopened["alpha"] == "1"
    assert db_reopened["beta"] == "2"
    assert db_reopened["gamma"] == "3"
    assert len(db_reopened) == 3
    assert "alpha" in db_reopened
    assert "zeta" not in db_reopened
    db_reopened.close()


def test_key_not_found_raises_keyerror(temp_db_path):
    db = connect(temp_db_path)
    with pytest.raises(KeyError):
        _ = db["non_existent"]
    db.close()


def test_delete_key_operation(temp_db_path):
    db = connect(temp_db_path)
    db["item_1"] = "val_1"
    db["item_2"] = "val_2"
    db.commit()

    del db["item_1"]
    db.commit()
    db.close()

    db_reopened = connect(temp_db_path)
    assert "item_1" not in db_reopened
    assert db_reopened["item_2"] == "val_2"
    assert len(db_reopened) == 1
    db_reopened.close()


def test_uncommitted_changes_are_not_persisted(temp_db_path):
    db = connect(temp_db_path)
    db["persisted"] = "initial"
    db.commit()

    db["persisted"] = "modified_uncommitted"
    db.close()

    db_reopened = connect(temp_db_path)
    assert db_reopened["persisted"] == "initial"
    db_reopened.close()


def test_cli_set_get_and_delete(temp_db_path, capsys):
    assert main(["tool.py", temp_db_path, "set", "cli_key", "cli_val"]) == 0

    assert main(["tool.py", temp_db_path, "get", "cli_key"]) == 0
    captured = capsys.readouterr()
    assert captured.out.strip() == "cli_val"

    assert main(["tool.py", temp_db_path, "delete", "cli_key"]) == 0

    assert main(["tool.py", temp_db_path, "get", "cli_key"]) == 1
    captured_err = capsys.readouterr()
    assert "KeyError" in captured_err.err