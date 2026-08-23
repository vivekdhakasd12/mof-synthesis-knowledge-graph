"""Human gold-standard annotation tool.

`core` holds all logic and is unit tested; `app` is the Streamlit front end and holds
none. Nothing in this package calls a model: the gold standard must be produced by the
human annotator, otherwise the evaluation it anchors would be circular.
"""
