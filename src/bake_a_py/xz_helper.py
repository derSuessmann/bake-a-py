"""Provide information about XZ file.

The code is based on the "specification" https://tukaani.org/xz/xz-file-format.txt 

"""

check_sum_algorithms = (
    # bytes, name
    (0, 'None'),
    (4, 'CRC32'),
    (4, '(Reserved)'),
    (4, '(Reserved)'),
    (8, 'CRC64'),
    (8, '(Reserved)'),
    (8, '(Reserved)'),
    (16, '(Reserved)'),
    (16, '(Reserved)'),
    (16, '(Reserved)'),
    (32,' SHA-256'),
    (32, '(Reserved)'),
    (32, '(Reserved)'),
    (64, '(Reserved)'),
    (64, '(Reserved)'),
    (64, '(Reserved)')
)

def xz_list(filename, verbose=False):
    with open(filename, 'rb') as f:
        magic = f.read(6)
        if magic != bytes.fromhex('fd377a585a00'):
            raise Exception('f{filename} has not XZ magic')

        stream_flags = f.read(2)

        stream_header_crc32 = f.read(4)

        if stream_flags[1] > len(check_sum_algorithms):
            raise Exception('check sum algorithm not supported')

        check_size, check_name = check_sum_algorithms[stream_flags[1]]

        if verbose:
            print(f'magic: {magic.hex()}')
            print(f'stream flags: {stream_flags.hex()} (checksum algo: {check_name} bytes: {check_size})')

        compressed_size, uncompressed_size = 0, 0

        while True:
            encoded_header_size = f.read(1)[0]
            if encoded_header_size == 0x00:
                read_index(f, verbose)
                break
            else:
                c, u = parse_block(f, check_size, encoded_header_size, verbose)

            if c is None or u is None: break

            compressed_size += c
            uncompressed_size += u

        stream_footer_crc32 = f.read(3)
        stream_footer_backward_size = f.read(4)
        stream_footer_flags = f.read(2)
        stream_footer_magic = f.read(2)

#        if stream_footer_magic != bytes.fromhex('595a'):
#            raise Exception('f{filename} has not XZ footer magic')
        
        if verbose:
            print(f'stream footer crc32: {stream_footer_crc32.hex()}')
            print(f'stream backward size: {int.from_bytes(stream_footer_backward_size, byteorder="little")}')
            print(f'stream flags: {stream_footer_flags.hex()}')
            print(f'magic: {stream_footer_magic.hex()}')

    return compressed_size, uncompressed_size

def parse_block(f, check_size, encoded_header_size, verbose):

    block_flags = f.read(1)[0]
    if block_flags & 0x3c:
        raise Exception('illegal block flags (0x{block_flags:x})')
    real_header_size = (encoded_header_size + 1) * 4

    remaining_bytes = real_header_size - 2

    if block_flags & 0x40: # contains compressed size
        read_bytes, compressed_size = multibyte_decode(f)
        remaining_bytes -= read_bytes
    else:
        compressed_size = None

    if block_flags & 0x80: # contains uncompressed size
        read_bytes, uncompressed_size = multibyte_decode(f)
        remaining_bytes -= read_bytes
    else:
        uncompressed_size = None

    number_of_filters = (block_flags & 0x03) + 1
    read_bytes, filter_flags = read_list_of_filter_flags(f, number_of_filters)
    remaining_bytes -= read_bytes
    
    # skip header padding
    pad = f.read(remaining_bytes - 4)

    crc32 = f.read(4)

    block_data_size = ((compressed_size + 3) // 4) * 4

    # skip block data
    f.read(compressed_size)

    padding = f.read(block_data_size - compressed_size)
    if sum(padding) != 0:
        raise Exception(f'block padding is {padding.hex()}')

    checksum = f.read(check_size)

    if verbose:
        print('block')
        print(f'  encoded header size: {encoded_header_size}, real header size: {real_header_size}')
        print(f'  block flags: {block_flags:x}')
        print(f'  compressed size: {compressed_size}')
        print(f'  uncompressed size: {uncompressed_size}')
        print(f'  number of filters: {number_of_filters}')
        for filter in filter_flags:
            print(f'    {filter}')
        print(f'  padding: {pad.hex()}')
        print(f'  block header crc32: {crc32.hex()}')
        print(f'  data checksum: {checksum.hex()}')

    return compressed_size, uncompressed_size

def read_list_of_filter_flags(f, number_of_filters):
    result = []
    read_bytes = 0
    while number_of_filters:
        n, filter = read_filter_flags(f)
        read_bytes += n
        result.append(filter)

        number_of_filters -= 1
    return read_bytes, result

def read_filter_flags(f):
    n, id = multibyte_decode(f)
    read_bytes = n

    n, size_of_properties = multibyte_decode(f)
    read_bytes += n

    properties = f.read(size_of_properties)
    read_bytes += size_of_properties

    return read_bytes, (id, size_of_properties, properties)

def read_index(f, verbose):
    if verbose:
        print('index')
    index_read_bytes, number_of_records = multibyte_decode(f)

    result = []
    for block_number in range(number_of_records):
        read_bytes, unpadded_size = multibyte_decode(f)
        index_read_bytes += read_bytes
        read_bytes, uncompressed_size = multibyte_decode(f)
        index_read_bytes += read_bytes
        
        if verbose:
            print(f'  block: {block_number}, unpadded: {unpadded_size}, uncompressed: {uncompressed_size}')
        result.append((block_number, unpadded_size, uncompressed_size))

    padding_size = ((index_read_bytes + 3) // 4) * 4 - index_read_bytes

    padding = f.read(padding_size)

    crc32 = f.read(4)

    if verbose:
        print(f'  padding: {padding.hex()}')
        print(f'  crc3: {crc32.hex()}')

    return result

def multibyte_decode(f):

    b = f.read(1)[0]

    i = 1
    result = b & 0x7f

    while b & 0x80:
        b = f.read(1)[0]

        result |= (b & 0x7f) << (7*i)

        i += 1

    return i, result

if __name__ == '__main__':
    import sys

    print(xz_list(sys.argv[1], verbose=True))
