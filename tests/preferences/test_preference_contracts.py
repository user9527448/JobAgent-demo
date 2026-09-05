"""Preference enum alignment checks."""

from typing import get_args

from jobagent.extraction import EDUCATION_ALIASES, REGION_ALIASES
from jobagent.preferences import EducationLevel, OrganizationType, RegionCode


def test_region_and_education_enums_stay_aligned_with_extraction_dictionaries() -> None:
    assert set(get_args(RegionCode)) == {value for value, _ in REGION_ALIASES}
    assert set(get_args(EducationLevel)) == {value for value, _ in EDUCATION_ALIASES}


def test_organization_types_are_employer_types_not_source_categories() -> None:
    assert set(get_args(OrganizationType)) == {
        "government",
        "public_institution",
        "state_owned",
        "private",
        "foreign_enterprise",
    }
    assert "public_exam" not in get_args(OrganizationType)
