"""Bound dictionaries for deterministic region and enum normalization."""

from __future__ import annotations

import re
import unicodedata
from typing import Final

REGION_ALIASES: Final[tuple[tuple[str, tuple[str, ...]], ...]] = (
    ("national", ("全国", "中国大陆", "mainland china", "nationwide")),
    ("beijing", ("北京市", "北京", "beijing")),
    ("tianjin", ("天津市", "天津", "tianjin")),
    ("hebei", ("河北省", "河北", "hebei")),
    ("shanxi", ("山西省", "山西", "shanxi")),
    ("inner_mongolia", ("内蒙古自治区", "内蒙古", "inner mongolia")),
    ("liaoning", ("辽宁省", "辽宁", "liaoning")),
    ("jilin", ("吉林省", "吉林", "jilin")),
    ("heilongjiang", ("黑龙江省", "黑龙江", "heilongjiang")),
    ("shanghai", ("上海市", "上海", "shanghai")),
    ("jiangsu", ("江苏省", "江苏", "jiangsu")),
    ("zhejiang", ("浙江省", "浙江", "zhejiang")),
    ("anhui", ("安徽省", "安徽", "anhui")),
    ("fujian", ("福建省", "福建", "fujian")),
    ("jiangxi", ("江西省", "江西", "jiangxi")),
    ("shandong", ("山东省", "山东", "shandong")),
    ("henan", ("河南省", "河南", "henan")),
    ("hubei", ("湖北省", "湖北", "hubei")),
    ("hunan", ("湖南省", "湖南", "hunan")),
    ("guangdong", ("广东省", "广东", "guangdong")),
    ("guangxi", ("广西壮族自治区", "广西", "guangxi")),
    ("hainan", ("海南省", "海南", "hainan")),
    ("chongqing", ("重庆市", "重庆", "chongqing")),
    ("sichuan", ("四川省", "四川", "sichuan")),
    ("guizhou", ("贵州省", "贵州", "guizhou")),
    ("yunnan", ("云南省", "云南", "yunnan")),
    ("tibet", ("西藏自治区", "西藏", "tibet")),
    ("shaanxi", ("陕西省", "陕西", "shaanxi")),
    ("gansu", ("甘肃省", "甘肃", "gansu")),
    ("qinghai", ("青海省", "青海", "qinghai")),
    ("ningxia", ("宁夏回族自治区", "宁夏", "ningxia")),
    ("xinjiang", ("新疆维吾尔自治区", "新疆", "xinjiang")),
    ("hong_kong", ("香港特别行政区", "香港", "hong kong")),
    ("macau", ("澳门特别行政区", "澳门", "macao", "macau")),
    ("taiwan", ("台湾省", "台湾", "taiwan")),
)

EDUCATION_ALIASES: Final[tuple[tuple[str, tuple[str, ...]], ...]] = (
    ("no_requirement", ("不限", "学历不限", "无学历要求", "no requirement")),
    ("doctorate", ("博士研究生", "博士", "phd", "doctorate")),
    (
        "master_or_above",
        ("硕士研究生及以上", "硕士及以上", "研究生及以上", "master or above"),
    ),
    ("master", ("硕士研究生", "硕士", "master", "master's degree")),
    ("bachelor_or_above", ("本科及以上", "大学本科及以上", "bachelor or above")),
    ("bachelor", ("大学本科", "本科", "bachelor", "bachelor's degree")),
    ("associate_or_above", ("大专及以上", "专科及以上", "associate or above")),
    ("associate", ("大学专科", "大专", "专科", "associate degree")),
    ("secondary_vocational", ("中等职业学校", "中职", "中专")),
    ("high_school", ("高中", "high school")),
)

CATEGORY_ALIASES: Final[tuple[tuple[str, tuple[str, ...]], ...]] = (
    ("campus", ("校园招聘", "校招", "应届生招聘", "campus recruitment")),
    ("civil_service", ("公务员招录", "公务员招聘", "公务员", "civil service")),
    ("public_institution", ("事业单位招聘", "事业单位", "public institution")),
    ("state_owned", ("央企招聘", "国企招聘", "state-owned enterprise")),
    ("social", ("社会招聘", "社招", "experienced hiring")),
)


def normalize_regions(raw_value: str) -> tuple[str, ...] | None:
    """Return provincial-level stable codes in source order without inference."""
    candidate = unicodedata.normalize("NFKC", raw_value).casefold()
    matches: list[tuple[int, str]] = []
    for code, aliases in REGION_ALIASES:
        positions = [
            position for alias in aliases if (position := _alias_position(candidate, alias)) >= 0
        ]
        if positions:
            matches.append((min(positions), code))
    matches.sort(key=lambda item: item[0])
    values = tuple(dict.fromkeys(code for _, code in matches))
    if len(values) > 1 and "national" in values:
        values = tuple(value for value in values if value != "national")
    return values or None


def normalize_education(raw_value: str) -> str | None:
    """Map an exact supported education requirement to its stable enum value."""
    return _normalize_exact_enum(raw_value, EDUCATION_ALIASES)


def normalize_category(raw_value: str) -> str | None:
    """Map an exact supported recruitment category to its stable enum value."""
    return _normalize_exact_enum(raw_value, CATEGORY_ALIASES)


def _normalize_exact_enum(
    raw_value: str,
    aliases_by_value: tuple[tuple[str, tuple[str, ...]], ...],
) -> str | None:
    candidate = _enum_key(raw_value)
    for value, aliases in aliases_by_value:
        if any(candidate == _enum_key(alias) for alias in aliases):
            return value
    return None


def _enum_key(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split()).strip(
        " ,\uff0c\u3002;\uff1b"
    )


def _alias_position(candidate: str, alias: str) -> int:
    normalized_alias = unicodedata.normalize("NFKC", alias).casefold()
    if normalized_alias.isascii():
        match = re.search(rf"(?<![a-z]){re.escape(normalized_alias)}(?![a-z])", candidate)
        return -1 if match is None else match.start()
    return candidate.find(normalized_alias)
