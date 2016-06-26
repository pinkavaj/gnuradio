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

from gnuradio import gr, gru
from gnuradio import blocks
from gnuradio import eng_notation
from gnuradio.eng_arg import eng_float, intx
from argparse import ArgumentParser

# From gr-digital
from gnuradio import digital

# from current dir
from receive_path import receive_path
from uhd_interface import uhd_receiver

import struct
import sys

#import os
#print os.getpid()
#raw_input('Attach and press enter: ')

class my_top_block(gr.top_block):
    def __init__(self, demodulator, rx_callback, options):
        gr.top_block.__init__(self)

        if(args.rx_freq is not None):
            # Work-around to get the modulation's bits_per_symbol
            args = demodulator.extract_kwargs_from_options(options)
            symbol_rate = args.bitrate / demodulator(**args).bits_per_symbol()

            self.source = uhd_receiver(args.args, symbol_rate,
                                       args.samples_per_symbol, args.rx_freq, 
                                       args.lo_offset, args.rx_gain,
                                       args.spec, args.antenna,
                                       args.clock_source, args.verbose)
            args.samples_per_symbol = self.source._sps

        elif(args.from_file is not None):
            sys.stderr.write(("Reading samples from '%s'.\n\n" % (args.from_file)))
            self.source = blocks.file_source(gr.sizeof_gr_complex, args.from_file)
        else:
            sys.stderr.write("No source defined, pulling samples from null source.\n\n")
            self.source = blocks.null_source(gr.sizeof_gr_complex)

        # Set up receive path
        # do this after for any adjustments to the options that may
        # occur in the sinks (specifically the UHD sink)
        self.rxpath = receive_path(demodulator, rx_callback, options) 

        self.connect(self.source, self.rxpath)


# /////////////////////////////////////////////////////////////////////////////
#                                   main
# /////////////////////////////////////////////////////////////////////////////

global n_rcvd, n_right

def main():
    global n_rcvd, n_right

    n_rcvd = 0
    n_right = 0
    
    def rx_callback(ok, payload):
        global n_rcvd, n_right
        (pktno,) = struct.unpack('!H', payload[0:2])
        n_rcvd += 1
        if ok:
            n_right += 1

        print "ok = %5s  pktno = %4d  n_rcvd = %4d  n_right = %4d" % (
            ok, pktno, n_rcvd, n_right)

    demods = digital.modulation_utils.type_1_demods()

    # Create Options Parser:
    parser = ArgumentParser(conflict_handler="resolve")
    expert_grp = parser.add_argument_group("Expert")

    parser.add_argument("-m", "--modulation", choices=demods.keys(),
                      default='psk',
                      help="Select modulation from: %s [default=%%(default)r]"
                            % (', '.join(demods.keys()),))
    parser.add_argument("--from-file",
                      help="input file of samples to demod")

    receive_path.add_arguments(parser, expert_grp)
    uhd_receiver.add_arguments(parser)

    for mod in demods.values():
        mod.add_arguments(expert_grp)

    args = parser.parse_args()

    if args.from_file is None:
        if args.rx_freq is None:
            sys.stderr.write("You must specify -f FREQ or --freq FREQ\n")
            parser.print_help(sys.stderr)
            sys.exit(1)


    # build the graph
    tb = my_top_block(demods[args.modulation], rx_callback, options)

    r = gr.enable_realtime_scheduling()
    if r != gr.RT_OK:
        print "Warning: Failed to enable realtime scheduling."

    tb.start()        # start flow graph
    tb.wait()         # wait for it to finish

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
