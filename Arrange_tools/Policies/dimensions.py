def check(item, policies, templates):
    if item['kind'] == 'slot':
        template = templates.get(item.get('template'))
        if template is None:
            return 'unknown_slot_template'
        if abs(item['length']-template['length']) > 1e-8 or abs(item['width']-template['width']) > 1e-8:
            return 'invalid_slot_dimensions'
    elif item['kind'] == 'road':
        if item['width'] not in policies['road_widths']:
            return 'road_width_must_be_3.5_or_6'
        if item['length'] <= 0 or item['length'] > 200:
            return 'invalid_road_length'
        if item['angle'] % 90 != 0:
            return 'roads_must_be_axis_aligned'
    else:
        return 'unknown_object_kind'
    return None
