import string

numeral_map = tuple(zip(
    (1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1),
    ('M', 'CM', 'D', 'CD', 'C', 'XC', 'L', 'XL', 'X', 'IX', 'V', 'IV', 'I')
))

def int_to_roman(i):
    result = []
    for integer, numeral in numeral_map:
        count = i // integer
        result.append(numeral * count)
        i -= integer * count
    return ''.join(result)

def roman_to_int(n):
    i = result = 0
    for integer, numeral in numeral_map:
        while n[i:i + len(numeral)] == numeral:
            result += integer
            i += len(numeral)
    return result

_nums = ('', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight',
    'Nine', 'Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen',
    'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen')

_tens = ( 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety')

def int_to_text(number):
    """Converts an integer to the English language name of that integer.
    
    E.g. converts 1 to "One". Supports numbers 0 to 999999.
    This can be used in LilyPond identifiers (that do not support digits).

    Included from python-ly project
    """
    result = []
    if number >= 1000:
        hundreds, number = divmod(number, 1000)
        result.append(int_to_text(hundreds) + "Thousand")
    if number >= 100:
        tens, number = divmod(number, 100)
        result.append(_nums[tens] + "Hundred")
    if number < 20:
        result.append(_nums[number])
    else:
        tens, number = divmod(number, 10)
        result.append(_tens[tens-2] + _nums[number])
    text = "".join(result)
    return text or 'Zero'

def int_to_letter(number, chars=string.ascii_uppercase):
    """Converts an integer to one or more letters.
    
    E.g. 1 -> A, 2 -> B, ... 26 -> Z, 27 -> AA, etc.
    Zero returns the empty string.
    
    chars is the string to pick characters from, defaulting to
    string.ascii_uppercase.
    
    """
    mod = len(chars)
    result = []
    while number > 0:
        number, c = divmod(number - 1, mod)
        result.append(c)
    return "".join(chars[c] for c in reversed(result))

def starts_with_one_of(strng, list_of_strings):
    """
    :param strng:
    :param list_of_strings:
    :return: true if strng starts with one of the entries in list_of_strings
    """
    for s in list_of_strings:
        if strng.startswith(s):
            return True
    return False

def is_valid_music_numeral(s):
    return s in ["I", "II", "III", "IV", "V", "VI", "VII", "VIII"]

def split_roman_prefix(s):
    """
    splits a roman numeral like VIbm7 into roman number, accidental, modifier
    :param s:(e.g. VIbm7)
    :return: (VI,b,m7)
    """
    for i in reversed(range(len(s)+1)):
        if i > 0:
            prefix = s[:i]
            if is_valid_music_numeral(prefix):
                num = roman_to_int(prefix)
                suffix = s[i:]
                accidental = ""
                if starts_with_one_of(suffix, ["bb", "##"]):
                    accidental = suffix[:2]
                    suffix = suffix[2:]
                elif starts_with_one_of(suffix, ["b", "#"]):
                    accidental = suffix[:1]
                    suffix = suffix[1:]
                return prefix, accidental, suffix
    return None, None, None


if __name__ == "__main__":
    print (int_to_roman(7))
    print (int_to_roman(1832))
    print (roman_to_int("IX"))
    print (roman_to_int("VII"))
    print (roman_to_int("XM"))
    print (int_to_text(12323))
    print (int_to_letter(28))
    print (split_roman_prefix("IVm"))
    print (split_roman_prefix("IV"))


