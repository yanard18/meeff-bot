"""UI state string constants.

All task is_eligible() checks and orchestrator code use these instead of
raw strings so that a renamed state is a single-file change.
"""

NOT_OPENED            = "NOT OPENED"
UNKNOWN_FAILED        = "UNKNOWN (Failed to read screen)"

QUIT_DIALOG           = "ACTIVE (Quit Dialog)"
SUGGEST_MEEFF         = "ACTIVE (Suggest Meeff)"
MATCH_COMPLETE        = "ACTIVE (Match Complete)"
AD                    = "ACTIVE (Ad)"
NATIVE_AD             = "ACTIVE (Native Ad)"

MATCHED_FRIEND_PROFILE = "ACTIVE (Matched Friend Profile)"
DETAILED_PROFILE       = "ACTIVE (Detailed Profile)"
SWIPE_MODE             = "ACTIVE (Swipe Mode)"
FIND_PAGE              = "ACTIVE (Find Page)"
CHAT_WITH_PERSON       = "ACTIVE (Chat With Person)"
CHAT_LIST              = "ACTIVE (Chat List)"
MY_PROFILE             = "ACTIVE (My Profile)"
SEARCH_FILTERS         = "ACTIVE (Search Filters)"
NATIONALITY_PICKER     = "ACTIVE (Nationality Picker)"
LIKE_VISITOR_PAGE      = "ACTIVE (Like/Visitor Page)"
TODAY_PAGE             = "ACTIVE (Today Page)"
UNKNOWN_SCREEN         = "ACTIVE (Unknown Screen/Ad)"

# Convenience sets for group-matching
DIALOG_STATES = {QUIT_DIALOG, SUGGEST_MEEFF, MATCH_COMPLETE, AD, NATIVE_AD}
