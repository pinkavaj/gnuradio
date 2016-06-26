#!/usr/bin/env python
#
# Copyright 2010,2011,2013 Free Software Foundation, Inc.
# 
# This file is part of GNU Radio
# 
# GNU Radio is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
# 
# GNU Radio is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with GNU Radio; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
# 

from gnuradio import gr
from gnuradio import blocks
from gnuradio import eng_notation
from gnuradio.eng_arg import eng_float, intx
from argparse import ArgumentParser

# From gr-digital
from gnuradio import digital

# from current dir
from transmit_path import transmit_path
from uhd_interface import uhd_transmitter

import time, struct, sys

#import os 
#print os.getpid()
#raw_input('Attach and press enter')

class my_top_block(gr.top_block):
    def __init__(self, modulator, options):
        gr.top_block.__init__(self)

        if(args.tx_freq is not None):
            # Work-around to get the modulation's bits_per_symbol
            args = modulator.extract_kwargs_from_options(options)
            symbol_rate = args.bitrate / modulator(**args).bits_per_symbol()

            self.sink = uhd_transmitter(args.args, symbol_rate,
                                        args.samples_per_symbol, args.tx_freq,
                                        args.lo_offset, args.tx_gain,
                                        args.spec, args.antenna,
                                        args.clock_source, args.verbose)
            args.samples_per_symbol = self.sink._sps
            
        elif(args.to_file is not None):
            sys.stderr.write(("Saving samples to '%s'.\n\n" % (args.to_file)))
            self.sink = blocks.file_sink(gr.sizeof_gr_complex, args.to_file)
        else:
            sys.stderr.write("No sink defined, dumping samples to null sink.\n\n")
            self.sink = blocks.null_sink(gr.sizeof_gr_complex)

        # do this after for any adjustments to the options that may
        # occur in the sinks (specifically the UHD sink)
        self.txpath = transmit_path(modulator, options)

        self.connect(self.txpath, self.sink)

# /////////////////////////////////////////////////////////////////////////////
#                                   main
# /////////////////////////////////////////////////////////////////////////////

def main():

    def send_pkt(payload='', eof=False):
        return tb.txpath.send_pkt(payload, eof)

    mods = digital.modulation_utils.type_1_mods()

    parser = ArgumentParser(conflict_handler="resolve")
    expert_grp = parser.add_argument_group("Expert")

    parser.add_argument("-m", "--modulation", type="choice", choices=mods.keys(),
                      default='psk',
                      help="Select modulation from: %s [default=%%(default)r]"
                            % (', '.join(mods.keys()),))

    parser.add_argument("-s", "--size", type=eng_float, default=1500,
                      help="set packet size [default=%(default)r]")
    parser.add_argument("-M", "--megabytes", type=eng_float, default=1.0,
                      help="set megabytes to transmit [default=%(default)r]")
    parser.add_argument("--discontinuous", action="store_true", default=False,
                      help="enable discontinous transmission (bursts of 5 packets)")
    parser.add_argument("--from-file", default=None,
                      help="use intput file for packet contents")
    parser.add_argument("--to-file", default=None,
                      help="Output file for modulated samples")

    transmit_path.add_arguments(parser, expert_grp)
    uhd_transmitter.add_arguments(parser)

    for mod in mods.values():
        mod.add_arguments(expert_grp)

    args = parser.parse_args()

    if args.from_file is not None:
        source_file = open(args.from_file, 'r')

    # build the graph
    tb = my_top_block(mods[args.modulation], options)

    r = gr.enable_realtime_scheduling()
    if r != gr.RT_OK:
        print "Warning: failed to enable realtime scheduling"

    tb.start()                       # start flow graph
        
    # generate and send packets
    nbytes = int(1e6 * args.megabytes)
    n = 0
    pktno = 0
    pkt_size = int(args.size)

    while n < nbytes:
        if args.from_file is None:
            data = (pkt_size - 2) * chr(pktno & 0xff) 
        else:
            data = source_file.read(pkt_size - 2)
            if data == '':
                break;

        payload = struct.pack('!H', pktno & 0xffff) + data
        send_pkt(payload)
        n += len(payload)
        sys.stderr.write('.')
        if args.discontinuous and pktno % 5 == 4:
            time.sleep(1)
        pktno += 1
        
    send_pkt(eof=True)

    tb.wait()                       # wait for it to finish

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
