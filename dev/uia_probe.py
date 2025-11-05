try:
    import uiautomation as uia
    r=uia.GetRootControl()
    print("ui_root_ok")
except Exception:
    print("ui_probe_skipped")
