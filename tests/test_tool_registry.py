"""Acceptance tests for Module 2.4: Tool Registry."""

import json
import pytest
from layer2_tools.tool_registry import ALL_TOOLS, check_complexity, check_security, check_structure


def test_tool_registry_contains_expected_tools():
    tool_names = {t.name for t in ALL_TOOLS}
    assert tool_names == {"check_structure", "check_security", "check_complexity"}


def test_tools_callable_via_langchain_invoke():
    sample_code = """
class OrderService:
    def process_order(self, order_id, is_admin):
        if is_admin:
            query = "SELECT * FROM orders WHERE id=" + str(order_id)
            return query
        return None
"""
    # 1. Test check_structure
    struct_res = check_structure.invoke({"code": sample_code})
    assert isinstance(struct_res, dict)
    assert "classes" in struct_res
    json_struct = json.dumps(struct_res)
    assert json_struct is not None

    # 2. Test check_security
    sec_res = check_security.invoke({"code": sample_code})
    assert isinstance(sec_res, list)
    json_sec = json.dumps(sec_res)
    assert json_sec is not None

    # 3. Test check_complexity
    comp_res = check_complexity.invoke({"code": sample_code})
    assert isinstance(comp_res, dict)
    assert "maintainability_index" in comp_res
    json_comp = json.dumps(comp_res)
    assert json_comp is not None
