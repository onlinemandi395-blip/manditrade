from __future__ import annotations

from modules.suta_mandi.dashboard import is_suta_material, list_suta_materials


def test_suta_material_filter_accepts_category_and_name_matches():
    materials = [
        {"raw_material_id": "RM001", "name": "Cotton Suta 20s", "category": "SUTA", "status": "ACTIVE"},
        {"raw_material_id": "RM002", "name": "Poly Yarn 30D", "category": "RAW_MATERIAL", "status": "ACTIVE"},
        {"raw_material_id": "RM003", "name": "Reactive Dye Blue", "category": "DYE", "status": "ACTIVE"},
        {"raw_material_id": "RM004", "name": "Cotton Suta 40s", "category": "SUTA", "status": "INACTIVE"},
    ]

    assert is_suta_material(materials[0]) is True
    assert is_suta_material(materials[1]) is True
    assert is_suta_material(materials[2]) is False
    assert [item["raw_material_id"] for item in list_suta_materials(materials)] == ["RM001", "RM002"]


def test_suta_mandi_page_is_positioned_as_manufacturer_only_supply_market():
    content = open("modules/suta_mandi/dashboard.py", encoding="utf-8").read()
    assert "Manufacturer-only suta purchasing market" in content
    assert "raw-material buying surface, not a finished-product market" in content
    assert "Suta Mandi is available only in manufacturer workspace context." in content
