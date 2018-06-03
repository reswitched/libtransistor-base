#!/usr/bin/env python

import struct, sys, hashlib
from elftools.elf.elffile import ELFFile
from elftools.elf.relocation import RelocationSection
from elftools.elf.sections import *
from itertools import *
import lz4.block
import argparse

R_AARCH64_ABS64 = 257
R_AARCH64_ABS32 = 258
R_AARCH64_ABS16 = 259
R_AARCH64_PREL64 = 260
R_AARCH64_PREL32 = 261
R_AARCH64_PREL16 = 262

def write_aset(fp, args):
	fp.write('ASET'.encode())
	fp.write(struct.pack('<I', 0))
	aset_size = 0x4 + 0x4 + 0x10 + 0x10 + 0x10

	icon_size = 0
	icon_data = bytes()

	nacp_size = 0x4000
	nacp_data = bytearray(nacp_size)

	# Currently unsupported
	romfs_size = 0
	romfs_data = bytes()

	# Load icon data
	if args.icon:
		with open(args.icon, 'rb') as fp_icon:
			icon_data = fp_icon.read()
			icon_size = len(icon_data)
		
	# Create the control.nacp structure
	if args.name or args.developer or args.version:
		name_encoded = args.name.encode()[:0x200]
		developer_encoded = args.developer.encode()[:0x100]
		version_encoded = args.version.encode()[:0x10]

		for lang_entry_index in range(12):
			name_start = lang_entry_index * 0x300
			name_end = name_start + len(name_encoded)

			developer_start = lang_entry_index * 0x300 + 0x200
			developer_end = developer_start + len(developer_encoded)

			nacp_data[name_start:name_end] = name_encoded
			nacp_data[developer_start:developer_end] = developer_encoded

		version_start = 0x3060
		version_end = version_start + len(version_encoded)
		nacp_data[version_start:version_end] = version_encoded

	fp.write(struct.pack('<QQ', aset_size, icon_size))
	fp.write(struct.pack('<QQ', aset_size + icon_size, nacp_size))
	fp.write(struct.pack('<QQ', aset_size + icon_size + nacp_size, romfs_size))

	fp.write(icon_data)
	fp.write(nacp_data)
	fp.write(romfs_data)

def main(args):
	format = args.format.lower()

	with open(args.infile, 'rb') as f:
		elffile = ELFFile(f)

		load_segments = list(filter(lambda x: x['p_type'] == 'PT_LOAD', elffile.iter_segments()))
		
		assert len(load_segments) == 4

		code_segment = load_segments[0]
		rodata_segment = load_segments[1]
		data_segment = load_segments[2]
		bss_segment = load_segments[3]

		assert code_segment['p_vaddr'] & 0xFFF == 0
		assert code_segment['p_flags'] == 5
		
		assert rodata_segment['p_vaddr'] & 0xFFF == 0
		assert rodata_segment['p_flags'] == 4
		
		assert data_segment['p_vaddr'] & 0xFFF == 0
		assert data_segment['p_flags'] == 6
		
		assert bss_segment['p_vaddr'] & 0xFFF == 0
		assert bss_segment['p_filesz'] == 0
		assert bss_segment['p_flags'] == 6

		def page_pad(data):
			return data + ('\0'.encode() * (((len(data) + 0xFFF) & ~0xFFF) - len(data)))
		
		code = page_pad(code_segment.data())
		rodata = page_pad(rodata_segment.data())
		data = page_pad(data_segment.data())
		
		if format == 'nro':
			# text = text[0x80:]
			with open(args.outfile, 'wb') as fp:
				dot = 0
				
				fp.write(code[:0x10]) # first branch instruction, mod0 offset, and padding
				
				# NRO header
				fp.write('NRO0'.encode())
				fp.write(struct.pack('<III', 0, len(code) + len(rodata) + len(data), 0))
				
				assert dot & 0xFFF == 0
				assert code_segment['p_vaddr'] == dot
				fp.write(struct.pack('<II', dot, len(code))) # exec segment
				dot+= len(code)
				
				assert dot & 0xFFF == 0
				assert rodata_segment['p_vaddr'] == dot
				fp.write(struct.pack('<II', dot, len(rodata))) # read only segment
				dot+= len(rodata)
				
				assert dot & 0xFFF == 0
				assert data_segment['p_vaddr'] == dot
				fp.write(struct.pack('<II', dot, len(data))) # rw segment
				dot+= len(data)

				assert dot & 0xFFF == 0
				assert bss_segment['p_vaddr'] == dot
				fp.write(struct.pack('<II', (bss_segment['p_memsz'] + 0xFFF) & ~0xFFF, 0))
				
				fp.write('\0'.encode() * 0x40)
				
				fp.write(code[0x80:])
				fp.write(rodata)
				fp.write(data)

				if args.name or args.developer or args.icon:
					write_aset(fp, args)
		else:
			with open(args.outfile, 'wb') as fp:
				ccode, crodata, cdata = [lz4.block.compress(x, store_size=False) for x in (code, rodata, data)]

				fp.write('NSO0'.encode())
				fp.write(struct.pack('<III', 0, 0, 0x3f))

				off = 0x100
				dot = 0

				assert dot & 0xFFF == 0
				assert code_segment['p_vaddr'] == dot
				fp.write(struct.pack('<IIII', off, dot, len(code), 0))
				off += len(ccode)
				dot += len(code)

				assert dot & 0xFFF == 0
				assert rodata_segment['p_vaddr'] == dot
				fp.write(struct.pack('<IIII', off, dot, len(rodata), 0))
				off += len(crodata)
				dot += len(rodata)

				assert dot & 0xFFF == 0
				assert data_segment['p_vaddr'] == dot
				fp.write(struct.pack('<IIII', off, dot, len(data), (bss_segment['p_memsz'] + 0xFFF) & ~0xFFF))
				off += len(cdata)
				dot += len(data)

				assert bss_segment['p_vaddr'] == dot

				fp.write('\0'.encode() * 0x20)
				
				fp.write(struct.pack('<IIII', len(ccode), len(crodata), len(cdata), 0))
				
				fp.write('\0'.encode() * 0x30)

				for x in (code, rodata, data):
					 m = hashlib.sha256()
					 m.update(x)
					 assert m.digest_size == 0x20
					 fp.write(m.digest())

				fp.write(ccode)
				fp.write(crodata)
				fp.write(cdata)


if __name__ == '__main__':
	parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
	parser.add_argument(
		'infile', 
		type=str, 
		help='Input ELF file to convert to NRO/NSO'
	)
	parser.add_argument(
		'outfile',
		type=str,
		help='Output NRO/NSO file'
	)
	parser.add_argument(
		'format',
		type=str,
		default='nro',
		choices=['nro', 'nso'],
		help='Output file format'
	)

	parser.add_argument(
		'-n', '--name',
		type=str,
		default='',
		help='Application name (requires `nro` format)'
	)
	parser.add_argument(
		'-d', '--developer',
		type=str,
		default='',
		help='Application developer (requires `nro` format)'
	)
	parser.add_argument(
		'-v', '--version',
		type=str,
		default='',
		help='Application version (requires `nro` format)'
	)
	parser.add_argument(
		'-i', '--icon',
		type=str,
		required=False,
		help='Path to application icon (256x256 JPEG; requires `nro` format)'
	)

	args = parser.parse_args()

	if args.format != 'nro' and (args.name or args.developer or args.version or args.icon):
		parser.error('--name, --developer, --version, and --icon require `nro` format')

	main(args)