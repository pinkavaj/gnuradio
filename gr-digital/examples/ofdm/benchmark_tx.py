#!/usr/bin/env python
#
# Copyright 2005,2006,2011,2013 Free Software Foundation, Inc.
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
from gnuradio import eng_notation
from gnuradio.eng_arg import eng_float, intx
from argparse import ArgumentParser
import time, struct, sys

from gnuradio import digital
from gnuradio import blocks

# from current dir
from transmit_path import transmit_path
from uhd_interface import uhd_transmitter

class my_top_block(gr.top_block):
    def __init__(self, options):
        gr.top_block.__init__(self)

        if(args.tx_freq is not None):
            self.sink = uhd_transmitter(args.args,
                                        args.bandwidth, args.tx_freq, 
                                        args.lo_offset, args.tx_gain,
                                        args.spec, args.antenna,
                                        args.clock_source, args.verbose)
        elif(args.to_file is not None):
            self.sink = blocks.file_sink(gr.sizeof_gr_complex, args.to_file)
        else:
            self.sink = blocks.null_sink(gr.sizeof_gr_complex)

        # do this after for any adjustments to the options that may
        # occur in the sinks (specifically the UHD sink)
        self.txpath = transmit_path(options)

        self.connect(self.txpath, self.sink)
        
# /////////////////////////////////////////////////////////////////////////////
#                                   main
# /////////////////////////////////////////////////////////////////////////////

def main():

    def send_pkt(payload='', eof=False):
        return tb.txpath.send_pkt(payload, eof)

    parser = ArgumentParser(conflict_handler="resolve")
    expert_grp = parser.add_argument_group("Expert")
    parser.add_argument("-s", "--size", type=eng_float, default=400,
                      help="set packet size [default=%default]")
    parser.add_argument("-M", "--megabytes", type=eng_float, default=1.0,
                      help="set megabytes to transmit [default=%default]")
    parser.add_argument("","--discontinuous", action="store_true", default=False,
                      help="enable discontinuous mode")
    parser.add_argument("","--from-file", default=None,
                      help="use intput file for packet contents")
    parser.add_argument("","--to-file", default=None,
                      help="Output file for modulated samples")

    transmit_path.add_arguments(parser, expert_grp)
    digital.ofdm_mod.add_arguments(parser, expert_grp)
    uhd_transmitter.add_arguments(parser)

    args = parser.parse_args()

    # build the graph
    tb = my_top_block(options)
    
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
    time.sleep(2)               # allow time for queued packets to be sent
    tb.wait()                   # wait for it to finish

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
