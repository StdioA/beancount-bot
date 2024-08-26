from conf.utils import merge_dicts


def test_merge_empty_dicts():
    dict1 = {}
    dict2 = {}
    expected = {}
    assert merge_dicts(dict1, dict2) == expected

def test_merge_dict_with_empty_dict():
    dict1 = {'a': 1, 'b': 2}
    dict2 = {}
    expected = {'a': 1, 'b': 2}
    assert merge_dicts(dict1, dict2) == expected

def test_merge_non_overlapping_keys():
    dict1 = {'a': 1, 'b': 2}
    dict2 = {'c': 3, 'd': 4}
    expected = {'a': 1, 'b': 2, 'c': 3, 'd': 4}
    assert merge_dicts(dict1, dict2) == expected

def test_merge_overlapping_keys_non_dict_values():
    dict1 = {'a': 1, 'b': 2}
    dict2 = {'b': 3, 'c': 4}
    expected = {'a': 1, 'b': 3, 'c': 4}
    assert merge_dicts(dict1, dict2) == expected

def test_merge_overlapping_keys_dict_values():
    dict1 = {'a': 1, 'b': {'x': 1, 'y': 2}}
    dict2 = {'b': {'y': 3, 'z': 4}}
    expected = {'a': 1, 'b': {'x': 1, 'y': 3, 'z': 4}}
    assert merge_dicts(dict1, dict2) == expected

def test_merge_deeply_nested_dict_values():
    dict1 = {'a': 1, 'b': {'x': 1, 'y': {'m': 1, 'n': 2}}}
    dict2 = {'b': {'y': {'n': 3, 'o': 4}}}
    expected = {'a': 1, 'b': {'x': 1, 'y': {'m': 1, 'n': 3, 'o': 4}}}
    assert merge_dicts(dict1, dict2) == expected
