"""MOD-B19 Live data (Amendment A2 §7.1): fetches and normalises open data for any-city mode.

The module owns no table. It returns plain data; the places module (MOD-B04) and the RAG module
(MOD-B18) store it. Nothing here runs while the switch ``any_city_mode`` is OFF.
"""
