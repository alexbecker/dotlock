from dotlock import json


def test_strip_sharp_comments():
    assert json.strip('# comment') == ''
    assert json.strip('  # comment') == '  '
    assert json.strip('  "foo": "bar" # baz') == '  "foo": "bar" '
    assert json.strip(r'  "foo": "bar\"" # baz') == r'  "foo": "bar\"" '
    assert json.strip(r'  "foo": "bar # baz" # baz') == r'  "foo": "bar # baz" '


def test_strip_slash_comments():
    assert json.strip('// comment') == ''
    assert json.strip('  // comment') == '  '
    assert json.strip('  "foo": "bar" // baz') == '  "foo": "bar" '
    assert json.strip(r'  "foo": "bar\"" // baz') == r'  "foo": "bar\"" '
    assert json.strip(r'  "foo": "bar // baz" // baz') == r'  "foo": "bar // baz" '


def test_strip_no_comments():
    assert json.strip('  "foo": "bar"') == '  "foo": "bar"'
    assert json.strip(r'  "foo": "bar\""') == r'  "foo": "bar\""'
    assert json.strip(r'  "foo": "bar // baz"') == r'  "foo": "bar // baz"'
    assert json.strip(r'  "foo": "bar # baz"') == r'  "foo": "bar # baz"'


def test_loads():
    assert json.loads(
r"""{
  "a": 1,
  "foo": true,
  "bar//": {
    "fun": "run\"in the sun", // remove me
    "baz": "simple json"      // me too
  },
  "array": [
    1,
    true,
    "boo"
  ]
}""") == {
        'a': 1,
        'foo': True,
        'bar//': {
            'fun': 'run"in the sun',
            'baz': 'simple json'
        },
        'array': [
            1,
            True,
            "boo"
        ]
    }
