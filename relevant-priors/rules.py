BODY_PART_GROUPS = {
    "HEAD":       ["BRAIN", "HEAD", "SKULL", "CRANIAL", "NEURO",
                   "ORBIT", "IAC", "PITUITARY", "SELLA", "STROKE"],
    "NECK":       ["NECK", "THYROID", "CERVICAL SOFT"],
    "CHEST":  ["CHEST", "THORAX", "LUNG", "PULMONARY",
                "CARDIAC", "HEART", "MEDIASTIN", "RIBS",
                "CORONARY", "SPECT", "MYOCARD", "NM MYO",
                "PIFLU", "F18"],

    "BREAST": ["BREAST", "MAM", "MAMMOGRAPH", 
           "DIGITAL SCREENER", "TOMOSYNTHESIS"],
    "US_BREAST": ["MAM US", "ULTRASOUND BREAST", "US BREAST",
              "ULTRASOUND BILAT", "ULTRASOUND LT DIAG",
              "ULTRASOUND RT DIAG"],
    "ABDOMEN":    ["ABDOMEN", "LIVER", "PANCREA", "RENAL", "KIDNEY",
                   "SPLEEN", "ADRENAL", "GALLBLADDER", "BILIARY"],
    "PELVIS":     ["PELVIS", "UTERUS", "OVARY", "PROSTATE",
                   "BLADDER", "RECTUM"],
    "ABD_PELVIS": ["ABD & PELVIS", "ABDOMEN AND PELVIS",
                   "ABD/PELVIS", "ABDOMEN/PELVIS"],
    "SPINE":      ["SPINE", "LUMBAR", "THORACIC SPINE",
                   "SACRAL", "LUMBO"],
    "SHOULDER":   ["SHOULDER", "ROTATOR", "CLAVICLE", "SCAPULA"],
    "ELBOW":      ["ELBOW"],
    "WRIST":      ["WRIST", "FOREARM"],
    "HAND":       ["HAND", "FINGER", "THUMB"],
    "HIP":        ["HIP", "FEMUR", "ACETABUL"],
    "KNEE":       ["KNEE", "PATELLA"],
    "ANKLE":      ["ANKLE", "FOOT", "CALCANEUS", "TOE"],
    "WHOLE_BODY": ["WHOLE BODY", "TOTAL BODY", "PET", "NUCLEAR"],
}

#Map a study_description to its body part group
def get_body_part_group(description: str) -> str | None:
    """
    Returns the group name if a keyword is found, otherwise None.

    Example:
        get_body_part_group("MRI BRAIN STROKE WITHOUT CONTRAST")
        -> "HEAD"
    """
    desc_upper = description.upper()

    # Check specific multi-word groups first to avoid false matches
    priority_groups = ["ABD_PELVIS", "WHOLE_BODY"]
    for group in priority_groups:
        for keyword in BODY_PART_GROUPS[group]:
            if keyword in desc_upper:
                return group

    # Check all remaining groups
    for group, keywords in BODY_PART_GROUPS.items():
        if group in priority_groups:
            continue
        for keyword in keywords:
            if keyword in desc_upper:
                return group

    return None  # Unknown body part


# Main relevance function
def is_relevant(current_description: str, prior_description: str) -> bool:
    """
    Returns True if the prior study is likely useful when reading
    the current study.

    Logic:
        - Same body part group  -> True
        - One or both unknown   -> False (conservative default)
        - WHOLE_BODY vs other   -> False (too broad to be specific)
    """
    current_group = get_body_part_group(current_description)
    prior_group = get_body_part_group(prior_description)

    # Both are whole-body scans (e.g. PET) -> relevant to each other
    if current_group == "WHOLE_BODY" and prior_group == "WHOLE_BODY":
        return True

    # One is whole-body, one is specific -> not reliable, return False
    if current_group == "WHOLE_BODY" or prior_group == "WHOLE_BODY":
        return False

    # Either description couldn't be parsed -> default False
    if current_group is None or prior_group is None:
        return False

    # Core rule: same anatomical region = relevant
    return current_group == prior_group