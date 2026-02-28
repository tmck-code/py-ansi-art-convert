#!/usr/bin/env python3
"Unit tests for SAUCE metadata parsing in sauce.py"

import pytest

from ansi_art_convert.encoding import SupportedEncoding
from ansi_art_convert.sauce import (
    ASPECT_RATIO_MAP,
    LETTER_SPACING_MAP,
    SauceRecord,
    SauceRecordExtended,
)


class TestSauceRecordOffsets:
    'Test SauceRecord.offsets() static method'

    def test_offsets_structure(self) -> None:
        offsets = SauceRecord.offsets()
        assert isinstance(offsets, dict)
        assert len(offsets) == 16

    def test_offsets_ranges(self) -> None:
        offsets = SauceRecord.offsets()
        assert offsets['ID'] == (0, 5)  # ID should start at 0 and end at 5
        assert offsets['version'] == (5, 7)  # Version should be 2 bytes starting at 5
        assert offsets['tinfo_s'] == (106, 128)  # TInfoS should end at 128 (last field)

    def test_offsets_no_gaps(self) -> None:
        'Ensure all offsets are contiguous with no gaps'

        offsets = SauceRecord.offsets()
        all_ranges = sorted(offsets.values())

        # First range should start at 0
        assert all_ranges[0][0] == 0

        # Each range should end where the next begins
        for i in range(len(all_ranges) - 1):
            assert all_ranges[i][1] == all_ranges[i + 1][0]

        # Last range should end at 128
        assert all_ranges[-1][1] == 128


class TestSauceRecordIsEmpty:
    'Test empty SauceRecord detection'

    def test_empty_record(self) -> None:
        record = SauceRecord()
        assert record.is_empty() is True

    def test_valid_record(self) -> None:
        record = SauceRecord(ID='SAUCE')
        assert record.is_empty() is False

    def test_invalid_id(self) -> None:
        record = SauceRecord(ID='WRONG')
        assert record.is_empty() is True


class TestSauceRecordParseField:
    'Test SauceRecord.parse_field() static method'

    def test_parse_integer_fields(self) -> None:
        'Test parsing of integer fields from bytes'

        # Test data_type
        result = SauceRecord.parse_field('data_type', b'\x01', 'cp437')
        assert result == 1
        assert isinstance(result, int)

        # Test tinfo1 (2-byte little-endian)
        result = SauceRecord.parse_field('tinfo1', b'\x50\x00', 'cp437')
        assert result == 80

        # Test filesize (4-byte little-endian)
        result = SauceRecord.parse_field('filesize', b'\xd2\x04\x00\x00', 'cp437')
        assert result == 1234

    def test_parse_string_fields(self) -> None:
        'Test parsing of string fields from bytes'

        # Test title
        result = SauceRecord.parse_field('title', b'Test Title\x00\x00', 'cp437')
        assert result == 'Test Title'
        assert isinstance(result, str)

        # Test author with null bytes
        result = SauceRecord.parse_field('author', b'Author\x00\x00\x00\x00', 'cp437')
        assert result == 'Author'

    def test_parse_field_with_encoding(self) -> None:
        'Test parsing with different encodings'

        # CP437 encoding
        result = SauceRecord.parse_field('title', b'Test\x00', 'cp437')
        assert result == 'Test'

        # ISO-8859-1 encoding
        result = SauceRecord.parse_field('title', b'Test\x00', 'iso-8859-1')
        assert result == 'Test'

    def test_parse_field_strips_nulls(self) -> None:
        'Test that null bytes are properly stripped'

        result = SauceRecord.parse_field('author', b'\x00\x00Test\x00\x00', 'cp437')
        assert result == 'Test'

    def test_parse_field_empty_string(self) -> None:
        'Test parsing empty or null-only fields'

        result = SauceRecord.parse_field('title', b'\x00\x00\x00', 'cp437')
        assert result == ''


class TestSauceRecordParseRecord:
    'Test SauceRecord.parse_record() static method'

    def test_parse_valid_record(self) -> None:
        'Test parsing a valid SAUCE record'

        file_data = b'Hello World'
        sauce_data = SauceRecord(
            ID='SAUCE',
            version='00',
            title='My Art',
            author='Artist',
            group='Crew',
            tinfo1=80,
            flags=1,
        )

        record, _data = SauceRecord.parse_record(
            file_data + sauce_data.record_bytes('cp437'),
            'cp437',
        )
        result = record._asdict()

        expected = {
            'ID': 'SAUCE',
            'version': '00',
            'title': 'My Art',
            'author': 'Artist',
            'group': 'Crew',
            'date': '',
            'filesize': 0,
            'data_type': 0,
            'file_type': 0,
            'tinfo1': 80,
            'tinfo2': 0,
            'tinfo3': 0,
            'tinfo4': 0,
            'comments': 0,
            'flags': 1,
            'tinfo_s': '',
        }
        assert result == expected

    def test_parse_no_sauce_record(self) -> None:
        'Test parsing file without SAUCE record'

        file_data = b'Just plain text data without SAUCE'

        record, data = SauceRecord.parse_record(file_data, 'cp437')

        assert record.is_empty() is True
        assert record.ID == ''
        assert data == 'Just plain text data without SAUCE'

    def test_parse_invalid_magic(self) -> None:
        'Test parsing with invalid SAUCE magic'

        file_data = b'Hello World'
        invalid_sauce = SauceRecord(ID='WRONG').record_bytes('cp437')
        full_data = file_data + invalid_sauce

        record, data = SauceRecord.parse_record(full_data, 'cp437')

        assert record.is_empty() is True

    def test_parse_multibyte_integers(self) -> None:
        'Test parsing of multi-byte integer fields'

        sauce_data = SauceRecord(
            ID='SAUCE', version='00', filesize=65535, tinfo1=1000, tinfo2=500
        ).record_bytes('cp437')
        full_data = b'x' + sauce_data

        record, data = SauceRecord.parse_record(full_data, 'cp437')

        assert record.filesize == 65535
        assert record.tinfo1 == 1000
        assert record.tinfo2 == 500

    def test_parse_all_fields(self) -> None:
        'Test that all fields are correctly parsed'

        sauce_data = SauceRecord(
            ID='SAUCE',
            version='00',
            title='Title',
            author='Author',
            group='Group',
            date='20240228',
            filesize=9999,
            data_type=1,
            file_type=1,
            tinfo1=80,
            tinfo2=25,
            tinfo3=0,
            tinfo4=0,
            comments=2,
            flags=1,
            tinfo_s='IBM VGA',
        ).record_bytes('cp437')
        full_data = b'data' + sauce_data

        record, data = SauceRecord.parse_record(full_data, 'cp437')
        result = record._asdict()

        expected = {
            'ID': 'SAUCE',
            'version': '00',
            'title': 'Title',
            'author': 'Author',
            'group': 'Group',
            'date': '20240228',
            'filesize': 9999,
            'data_type': 1,
            'file_type': 1,
            'tinfo1': 80,
            'tinfo2': 25,
            'tinfo3': 0,
            'tinfo4': 0,
            'comments': 2,
            'flags': 1,
            'tinfo_s': 'IBM VGA',
        }
        assert result == expected


class TestSauceRecordExtendedParseComments:
    'Test SauceRecordExtended.parse_comments() static method'

    def test_parse_single_comment(self) -> None:
        'Test parsing a single comment'

        comment_block = SauceRecordExtended.write_comments(['First comment'])
        result = SauceRecordExtended.parse_comments(comment_block, 1)

        expected = ['First comment']
        assert result == expected

    def test_parse_multiple_comments(self) -> None:
        'Test parsing multiple comments'

        comment_block = SauceRecordExtended.write_comments(
            [
                'Comment line 1',
                'Comment line 2',
                'Comment line 3',
            ]
        )
        result = SauceRecordExtended.parse_comments(comment_block, 3)

        expected = [
            'Comment line 1',
            'Comment line 2',
            'Comment line 3',
        ]
        assert result == expected

    def test_parse_comment_strips_nulls(self) -> None:
        'Test that trailing nulls are stripped from comments'

        comment_block = 'COMNT' + 'Test comment with trailing nulls'.ljust(64, '\x00')
        result = SauceRecordExtended.parse_comments(comment_block, 1)

        expected = ['Test comment with trailing nulls']
        assert result == expected

    def test_parse_comment_invalid_size(self) -> None:
        'Test error handling for invalid comment block size'

        # size is 5 + 100, should be 5 + n*64 for n=2
        invalid_block = b'COMNT' + b'x' * 100

        with pytest.raises(ValueError, match='Invalid comment block size'):
            SauceRecordExtended.parse_comments(str(invalid_block), 2)

    def test_parse_empty_comments(self) -> None:
        'Test parsing comment blocks with empty/null-padded comments'

        comment_block = SauceRecordExtended.write_comments(['', ''])
        result = SauceRecordExtended.parse_comments(comment_block, 2)

        expected = ['', '']
        assert result == expected


class TestSauceRecordExtendedParseFlags:
    'Test SauceRecordExtended.parse_flags() static method'

    def test_parse_no_flags(self) -> None:
        'Test parsing flags when all bits are 0'

        result = SauceRecordExtended.parse_flags(0)
        expected = {
            'aspect_ratio': 'Legacy value. No preference.',
            'letter_spacing': 'Legacy value. No preference.',
            'non_blink_mode': False,
        }
        assert result == expected

    def test_parse_non_blink_mode(self) -> None:
        'Test parsing non-blink mode flag (bit 0)'

        result = SauceRecordExtended.parse_flags(1)  # Binary: 00000001

        assert result['non_blink_mode'] is True

    def test_parse_aspect_ratio_flags(self) -> None:
        'Test parsing aspect ratio bits'

        # Test (0, 1) - legacy device
        result = SauceRecordExtended.parse_flags(0b00001000)  # Bit 3 set
        assert 'legacy device' in result['aspect_ratio'].lower()

        # Test (1, 0) - modern device
        result = SauceRecordExtended.parse_flags(0b00010000)  # Bit 4 set
        assert 'modern device' in result['aspect_ratio'].lower()

    def test_parse_letter_spacing_flags(self) -> None:
        'Test parsing letter spacing bits'

        # Test (0, 1) - 8 pixel font (ls1=0, ls2=1, so bit 1 set)
        result = SauceRecordExtended.parse_flags(0b00000010)  # Bit 1 set
        assert '8 pixel' in result['letter_spacing']

        # Test (1, 0) - 9 pixel font (ls1=1, ls2=0, so bit 2 set)
        result = SauceRecordExtended.parse_flags(0b00000100)  # Bit 2 set
        assert '9 pixel' in result['letter_spacing']

    def test_parse_ice_colours_flag(self) -> None:
        'Test ICE colors flag (same as non_blink_mode)'

        result = SauceRecordExtended.parse_flags(0b00000001)
        assert result['non_blink_mode'] is True

    def test_parse_all_flags_set(self) -> None:
        'Test parsing with multiple flags set'

        result = SauceRecordExtended.parse_flags(0b11111111)

        assert result['non_blink_mode'] is True
        assert 'aspect_ratio' in result
        assert 'letter_spacing' in result


class TestSauceRecordExtendedParseFont:
    'Test SauceRecordExtended.parse_font() static method'

    def test_parse_ibm_vga_font(self) -> None:
        'Test parsing IBM VGA font'

        result = SauceRecordExtended.parse_font('IBM VGA')

        assert isinstance(result, dict)
        assert result['name'] == 'IBM VGA'
        assert 'font_size' in result
        assert result['font_size'] == '9x16'

    def test_parse_unknown_font(self) -> None:
        'Test parsing unknown font returns empty dict'

        result = SauceRecordExtended.parse_font('Unknown Font')

        assert result == {}

    def test_parse_empty_font_name(self) -> None:
        'Test parsing empty font name'

        result = SauceRecordExtended.parse_font('')

        assert result == {}

    def test_parse_font_with_whitespace(self) -> None:
        'Test that font name with whitespace is handled'

        result = SauceRecordExtended.parse_font('IBM VGA  ')

        # Should not match due to trailing spaces
        assert result == {}


class TestSauceRecordExtendedParseTinfoField:
    'Test SauceRecordExtended.parse_tinfo_field() static method'

    def test_parse_width_field(self) -> None:
        'Test parsing tinfo1 (width) for ANSi file'

        sauce = SauceRecord(
            data_type=1,
            file_type=1,  # ANSi
            tinfo1=80,
        )

        result = SauceRecordExtended.parse_tinfo_field('tinfo1', sauce)

        assert result['name'] == 'Character width'
        assert result['value'] == 80

    def test_parse_height_field(self) -> None:
        'Test parsing tinfo2 (height) for ANSi file'

        sauce = SauceRecord(data_type=1, file_type=1, tinfo2=25)

        result = SauceRecordExtended.parse_tinfo_field('tinfo2', sauce)

        assert result['name'] == 'Number of lines'
        assert result['value'] == 25

    def test_parse_zero_field(self) -> None:
        'Test parsing field that should be 0'

        sauce = SauceRecord(data_type=1, file_type=1, tinfo3=0)

        result = SauceRecordExtended.parse_tinfo_field('tinfo3', sauce)

        assert result['name'] == '0'
        assert result['value'] == 0

    def test_parse_tinfo_binary_text_not_implemented(self) -> None:
        'Test that data_type 5 (BinaryText) raises NotImplementedError'

        sauce = SauceRecord(data_type=5, file_type=0)

        with pytest.raises(NotImplementedError, match='BinaryText'):
            SauceRecordExtended.parse_tinfo_field('tinfo1', sauce)

    def test_parse_tinfo_ascii_file(self) -> None:
        'Test parsing tinfo for ASCII file (data_type=1, file_type=0)'

        sauce = SauceRecord(data_type=1, file_type=0, tinfo1=80, tinfo2=25)

        result1 = SauceRecordExtended.parse_tinfo_field('tinfo1', sauce)
        result2 = SauceRecordExtended.parse_tinfo_field('tinfo2', sauce)

        assert result1['name'] == 'Character width'
        assert result2['name'] == 'Number of lines'


class TestSauceRecordExtendedParseTinfo:
    'Test SauceRecordExtended.parse_tinfo() static method'

    def test_parse_tinfo_ansi_file(self) -> None:
        'Test parsing tinfo dict for ANSi file'

        sauce = SauceRecord(
            data_type=1, file_type=1, tinfo1=80, tinfo2=25, tinfo3=0, tinfo4=0
        )

        result = SauceRecordExtended.parse_tinfo(sauce)

        assert 'tinfo1' in result
        assert 'tinfo2' in result
        assert result['tinfo1']['value'] == 80
        assert result['tinfo2']['value'] == 25

    def test_parse_tinfo_excludes_zero_fields(self) -> None:
        'Test that fields with name "0" are excluded'
        sauce = SauceRecord(
            data_type=1, file_type=1, tinfo1=80, tinfo2=0, tinfo3=0, tinfo4=0
        )

        result = SauceRecordExtended.parse_tinfo(sauce)

        # tinfo1 should be included
        assert 'tinfo1' in result
        # tinfo2 with value 0 should be included (it's number of lines)
        assert 'tinfo2' in result
        # tinfo3 and tinfo4 should be excluded (name is '0')
        assert 'tinfo3' not in result
        assert 'tinfo4' not in result


class TestSauceRecordExtendedParse:
    'Test SauceRecordExtended.parse() static method'

    def test_parse_without_comments(self) -> None:
        'Test parsing SAUCE record without comments'

        file_data_content = 'Hello ANSI Art'
        sauce = SauceRecord(
            ID='SAUCE',
            version='00',
            title='Test',
            author='Author',
            data_type=1,
            file_type=1,
            tinfo1=80,
            comments=0,
            flags=0,
            tinfo_s='IBM VGA',
        )

        extended, data = SauceRecordExtended.parse(
            sauce, file_data_content, '/test/file.ans', SupportedEncoding.CP437
        )

        assert extended.fpath == '/test/file.ans'
        assert extended.encoding == SupportedEncoding.CP437
        assert extended.sauce == sauce
        assert extended.comments_data == []
        assert extended.non_blink_mode is False
        assert extended.ice_colours is False
        assert data == file_data_content

    def test_parse_with_ice_colours(self) -> None:
        'Test parsing SAUCE record with ICE colors flag'

        sauce = SauceRecord(
            ID='SAUCE',
            data_type=1,
            file_type=1,
            tinfo1=80,
            flags=1,  # Non-blink mode enabled
            tinfo_s='IBM VGA',
        )

        extended, data = SauceRecordExtended.parse(
            sauce, 'data', '/test/file.ans', SupportedEncoding.CP437
        )

        assert extended.non_blink_mode is True
        assert extended.ice_colours is True

    def test_parse_with_comments(self) -> None:
        'Test parsing SAUCE record configuration for comments'

        # Note: Full comment block extraction requires specific file structure with EOF markers
        # This test verifies the parse method handles the comments parameter correctly
        file_content = 'ANSI art data'

        sauce = SauceRecord(
            ID='SAUCE',
            data_type=1,
            file_type=1,
            tinfo1=80,
            comments=2,
            flags=0,
            tinfo_s='IBM VGA',
        )

        # Parse without actual comment block (will gracefully return empty comments)
        extended, data = SauceRecordExtended.parse(
            sauce, file_content, '/test/file.ans', SupportedEncoding.CP437
        )

        # Verify parse completes and handles missing comments gracefully
        assert extended.sauce.comments == 2
        assert isinstance(extended.comments_data, list)
        assert data == file_content

    def test_parse_with_font_data(self) -> None:
        'Test that font data is properly parsed'

        sauce = SauceRecord(
            ID='SAUCE', data_type=1, file_type=1, tinfo_s='IBM VGA', flags=0
        )

        extended, data = SauceRecordExtended.parse(
            sauce, 'data', '/test/file.ans', SupportedEncoding.CP437
        )

        assert extended.font != {}
        assert extended.font['name'] == 'IBM VGA'

    def test_parse_with_invalid_comments(self) -> None:
        'Test parsing with invalid comment block (graceful fallback)'

        # Invalid comment block (wrong size)
        file_content = 'ANSI art data'
        invalid_comments = 'COMNTbad'
        full_data = file_content + invalid_comments

        sauce = SauceRecord(
            ID='SAUCE', data_type=1, file_type=1, comments=1, flags=0, tinfo_s='IBM VGA'
        )

        # Should handle gracefully and return original data
        extended, data = SauceRecordExtended.parse(
            sauce, full_data, '/test/file.ans', SupportedEncoding.CP437
        )

        assert extended.comments_data == []
        assert data == full_data


class TestSauceRecordExtendedAsDict:
    'Test SauceRecordExtended.asdict() method'

    def test_asdict_structure(self) -> None:
        'Test that asdict returns proper structure'

        sauce = SauceRecord(
            ID='SAUCE',
            title='Test',
            data_type=1,
            file_type=1,
            tinfo1=80,
            tinfo_s='IBM VGA',
        )

        extended = SauceRecordExtended(
            fpath='/test/file.ans',
            encoding=SupportedEncoding.CP437,
            sauce=sauce,
            comments_data=['Comment 1'],
            font={'name': 'IBM VGA'},
            tinfo={},
            aspect_ratio='Legacy',
            letter_spacing='8 pixel',
            non_blink_mode=True,
            ice_colours=True,
        )

        result = extended.asdict()

        assert 'sauce' in result
        assert 'extended' in result
        assert isinstance(result['sauce'], dict)
        assert isinstance(result['extended'], dict)

    def test_sauce_fields(self) -> None:
        'Test that sauce section contains all SAUCE fields'

        sauce = SauceRecord(ID='SAUCE', version='00', title='Title', author='Author')

        extended = SauceRecordExtended(
            fpath='/test/file.ans',
            encoding=SupportedEncoding.CP437,
            sauce=sauce,
            comments_data=[],
            font={},
            tinfo={},
            aspect_ratio='',
            letter_spacing='',
            non_blink_mode=False,
            ice_colours=False,
        )
        result = extended.asdict()

        expected = {
            'extended': {
                'aspect_ratio': '',
                'comments': [],
                'encoding': 'cp437',
                'file_name': 'file.ans',
                'font': {},
                'ice_colours': False,
                'letter_spacing': '',
                'non_blink_mode': False,
                'tinfo': {},
            },
            'sauce': {
                'ID': 'SAUCE',
                'author': 'Author',
                'comments': 0,
                'data_type': 0,
                'date': '',
                'file_type': 0,
                'filesize': 0,
                'flags': 0,
                'group': '',
                'tinfo1': 0,
                'tinfo2': 0,
                'tinfo3': 0,
                'tinfo4': 0,
                'tinfo_s': '',
                'title': 'Title',
                'version': '00',
            },
        }
        assert result == expected

    def test_extended_fields(self) -> None:
        'Test that extended section contains extended metadata'

        sauce = SauceRecord(ID='SAUCE', tinfo1=80)

        extended = SauceRecordExtended(
            fpath='/path/to/file.ans',
            encoding=SupportedEncoding.CP437,
            sauce=sauce,
            comments_data=['Test comment'],
            font={'name': 'IBM VGA'},
            tinfo={'tinfo1': {'name': 'Character width', 'value': 80}},
            aspect_ratio='Modern',
            letter_spacing='9 pixel',
            non_blink_mode=True,
            ice_colours=True,
        )

        result = extended.asdict()
        expected = {
            'extended': {
                'aspect_ratio': 'Modern',
                'comments': [
                    'Test comment',
                ],
                'encoding': 'cp437',
                'file_name': 'file.ans',
                'font': {
                    'name': 'IBM VGA',
                },
                'ice_colours': True,
                'letter_spacing': '9 pixel',
                'non_blink_mode': True,
                'tinfo': {
                    'tinfo1': {
                        'name': 'Character width',
                        'value': 80,
                    },
                },
            },
            'sauce': {
                'ID': 'SAUCE',
                'author': '',
                'comments': 0,
                'data_type': 0,
                'date': '',
                'file_type': 0,
                'filesize': 0,
                'flags': 0,
                'group': '',
                'tinfo1': 80,
                'tinfo2': 0,
                'tinfo3': 0,
                'tinfo4': 0,
                'tinfo_s': '',
                'title': '',
                'version': '',
            },
        }
        assert result == expected

    def test_asdict_filename_extraction(self) -> None:
        'Test that file_name is correctly extracted from fpath'

        sauce = SauceRecord(ID='SAUCE')

        extended = SauceRecordExtended(
            fpath='/home/user/artwork/myfile.ans',
            encoding=SupportedEncoding.CP437,
            sauce=sauce,
            comments_data=[],
            font={},
            tinfo={},
            aspect_ratio='',
            letter_spacing='',
            non_blink_mode=False,
            ice_colours=False,
        )

        result = extended.asdict()

        assert result['extended']['file_name'] == 'myfile.ans'


class TestSauceConstants:
    'Test SAUCE constant definitions'

    def test_aspect_ratio_map_keys(self) -> None:
        'Test that ASPECT_RATIO_MAP has expected keys'

        assert (0, 0) in ASPECT_RATIO_MAP
        assert (0, 1) in ASPECT_RATIO_MAP
        assert (1, 0) in ASPECT_RATIO_MAP
        assert (1, 1) in ASPECT_RATIO_MAP

    def test_letter_spacing_map_keys(self) -> None:
        'Test that LETTER_SPACING_MAP has expected keys'

        assert (0, 0) in LETTER_SPACING_MAP
        assert (0, 1) in LETTER_SPACING_MAP
        assert (1, 0) in LETTER_SPACING_MAP
        assert (1, 1) in LETTER_SPACING_MAP

    def test_aspect_ratio_descriptions(self) -> None:
        'Test that aspect ratio descriptions are meaningful'

        for key, value in ASPECT_RATIO_MAP.items():
            assert isinstance(value, str)
            assert len(value) > 0

    def test_letter_spacing_descriptions(self) -> None:
        'Test that letter spacing descriptions are meaningful'

        for key, value in LETTER_SPACING_MAP.items():
            assert isinstance(value, str)
            assert len(value) > 0


class TestSauceIntegration:
    'Integration tests for complete SAUCE parsing workflow'

    def test_parse(self) -> None:
        'Test complete workflow from binary to SauceRecordExtended'

        file_content = b'This is ANSI art content'
        sauce_binary = SauceRecord(
            ID='SAUCE',
            title='My Artwork',
            author='Artist Name',
            group='Art Group',
            date='20240228',
            tinfo1=80,
            tinfo2=25,
            flags=1,
            tinfo_s='IBM VGA',
        )

        sauce, data = SauceRecord.parse_record(
            file_content + sauce_binary.record_bytes('cp437'),
            'cp437',
        )

        extended, _final_data = SauceRecordExtended.parse(
            sauce, data, '', SupportedEncoding.CP437
        )
        result = extended.asdict()

        expected = {
            'extended': {
                'aspect_ratio': 'Legacy value. No preference.',
                'comments': [],
                'encoding': 'cp437',
                'file_name': '',
                'font': {
                    'aspect_ratio': '4:3',
                    'description': 'Standard hardware font on VGA cards for 80x25 text mode (code '
                    'page 437)',
                    'font_size': '9x16',
                    'name': 'IBM VGA',
                    'pixel_aspect_ratio': '20:27 (1:1.35)',
                    'resolution': '720x400',
                    'vertical_stretch': '35%',
                },
                'ice_colours': True,
                'letter_spacing': 'Legacy value. No preference.',
                'non_blink_mode': True,
                'tinfo': {},
            },
            'sauce': {
                'ID': 'SAUCE',
                'author': 'Artist Name',
                'comments': 0,
                'data_type': 0,
                'date': '20240228',
                'file_type': 0,
                'filesize': 0,
                'flags': 1,
                'group': 'Art Group',
                'tinfo1': 80,
                'tinfo2': 25,
                'tinfo3': 0,
                'tinfo4': 0,
                'tinfo_s': 'IBM VGA',
                'title': 'My Artwork',
                'version': '',
            },
        }

        assert result == expected

    def test_parse_file_with_comments(self) -> None:
        'Test full workflow from binary to SauceRecordExtended (without comments)'

        # Note: Comment block extraction requires specific file structure (EOF markers, etc.)
        # This test verifies the basic workflow works
        file_content = b'Art data here'
        sauce_binary = SauceRecord(
            ID='SAUCE',
            title='Test Art',
            author='Test Artist',
            comments=1,
            flags=1,  # ICE colors enabled
            tinfo_s='IBM VGA',
        )
        comment_block = SauceRecordExtended.write_comments(
            [
                'comment 1',
            ]
        )

        sauce, data = SauceRecord.parse_record(
            file_content
            + comment_block.encode('cp437')
            + sauce_binary.record_bytes('cp437'),
            'cp437',
        )
        expected = {
            'ID': 'SAUCE',
            'author': 'Test Artist',
            'comments': 1,
            'data_type': 0,
            'date': '',
            'file_type': 0,
            'filesize': 0,
            'flags': 1,
            'group': '',
            'tinfo1': 0,
            'tinfo2': 0,
            'tinfo3': 0,
            'tinfo4': 0,
            'tinfo_s': 'IBM VGA',
            'title': 'Test Art',
            'version': '',
        }
        assert sauce._asdict() == expected

        extended, final_data = SauceRecordExtended.parse(
            sauce, data, '/test/art.ans', SupportedEncoding.CP437
        )
        assert final_data == 'Art data here'

        result = extended.asdict()
        expected = {
            'extended': {
                'aspect_ratio': 'Legacy value. No preference.',
                'comments': ['comment 1'],
                'encoding': 'cp437',
                'file_name': 'art.ans',
                'font': {
                    'aspect_ratio': '4:3',
                    'description': 'Standard hardware font on VGA cards for 80x25 text mode (code page 437)',
                    'font_size': '9x16',
                    'name': 'IBM VGA',
                    'pixel_aspect_ratio': '20:27 (1:1.35)',
                    'resolution': '720x400',
                    'vertical_stretch': '35%',
                },
                'ice_colours': True,
                'letter_spacing': 'Legacy value. No preference.',
                'non_blink_mode': True,
                'tinfo': {},
            },
            'sauce': {
                'ID': 'SAUCE',
                'author': 'Test Artist',
                'comments': 1,
                'data_type': 0,
                'date': '',
                'file_type': 0,
                'filesize': 0,
                'flags': 1,
                'group': '',
                'tinfo1': 0,
                'tinfo2': 0,
                'tinfo3': 0,
                'tinfo4': 0,
                'tinfo_s': 'IBM VGA',
                'title': 'Test Art',
                'version': '',
            },
        }

        assert result == expected
