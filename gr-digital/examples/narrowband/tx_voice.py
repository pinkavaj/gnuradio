#!/usr/bin/env python
#
# Copyright 2005-2007,2009,2011,2013 Free Software Foundation, Inc.
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

from gnuradio import gr, audio, uhd
from gnuradio import eng_notation
from gnuradio.eng_arg import eng_float, intx
from argparse import ArgumentParser

from gnuradio import blocks
from gnuradio import filter
from gnuradio import digital
from gnuradio import vocoder

import random
import time
import struct
import sys

# from current dir
from transmit_path import transmit_path
from uhd_interface import uhd_transmitter

#import os
#print os.getpid()
#raw_input('Attach and press enter')


class audio_rx(gr.hier_block2):
    def __init__(self, audio_input_dev):
	gr.hier_block2.__init__(self, "audio_rx",
				gr.io_signature(0, 0, 0), # Input signature
				gr.io_signature(0, 0, 0)) # Output signature
        self.sample_rate = sample_rate = 8000
        src = audio.source(sample_rate, audio_input_dev)
        src_scale = blocks.multiply_const_ff(32767)
        f2s = blocks.float_to_short()
        voice_coder = vocoder.gsm_fr_encode_sp()
        self.packets_from_encoder = gr.msg_queue()
        packet_sink = blocks.message_sink(33, self.packets_from_encoder, False)
        self.connect(src, src_scale, f2s, voice_coder, packet_sink)

    def get_encoded_voice_packet(self):
        return self.packets_from_encoder.delete_head()
        

class my_top_block(gr.top_block):

    def __init__(self, modulator_class, options):
        gr.top_block.__init__(self)
        self.txpath = transmit_path(modulator_class, options)
        self.audio_rx = audio_rx(args.audio_input)

        if(args.tx_freq is not None):
            self.sink = uhd_transmitter(args.address, args.bitrate,
                                        args.samples_per_symbol,
                                        args.tx_freq, args.tx_gain,
                                        args.antenna, args.verbose)
            args.samples_per_symbol = self.sink._sps
            audio_rate = self.audio_rx.sample_rate
            usrp_rate = self.sink.get_sample_rate()
            rrate = usrp_rate / audio_rate
            
        elif(args.to_file is not None):
            self.sink = blocks.file_sink(gr.sizeof_gr_complex, args.to_file)
            rrate = 1
        else:
            self.sink = blocks.null_sink(gr.sizeof_gr_complex)
            rrate = 1

        self.resampler = filter.pfb.arb_resampler_ccf(rrate)
            
	self.connect(self.audio_rx)
	self.connect(self.txpath, self.resampler, self.sink)
            

# /////////////////////////////////////////////////////////////////////////////
#                                   main
# /////////////////////////////////////////////////////////////////////////////

def main():

    def send_pkt(payload='', eof=False):
        return tb.txpath.send_pkt(payload, eof)

    def rx_callback(ok, payload):
        print "ok = %r, payload = '%s'" % (ok, payload)

    mods = digital.modulation_utils.type_1_mods()

    parser = ArgumentParser(conflict_handler="resolve")
    expert_grp = parser.add_argument_group("Expert")

    parser.add_argument("-m", "--modulation", choices=mods.keys(),
                      default='gmsk',
                      help="Select modulation from: %s [default=%%(default)r]"
                            % (', '.join(mods.keys()),))
    parser.add_argument("-M", "--megabytes", type=eng_float, default=0,
                      help="set megabytes to transmit [default=inf]")
    parser.add_argument("-I", "--audio-input", default="",
                      help="pcm input device name.  E.g., hw:0,0 or /dev/dsp")
    parser.add_argument("--to-file",
                      help="Output file for modulated samples")

    transmit_path.add_arguments(parser, expert_grp)
    uhd_transmitter.add_arguments(parser)

    for mod in mods.values():
        mod.add_arguments(expert_grp)

    parser.set_defaults(bitrate=50e3)  # override default bitrate default
    args = parser.parse_args()

    if args.to_file is None:
        if args.tx_freq is None:
            sys.stderr.write("You must specify -f FREQ or --freq FREQ\n")
            parser.print_help(sys.stderr)
            sys.exit(1)

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

    while nbytes == 0 or n < nbytes:
        packet = tb.audio_rx.get_encoded_voice_packet()
        s = packet.to_string()
        send_pkt(s)
        n += len(s)
        sys.stderr.write('.')
        pktno += 1
        
    send_pkt(eof=True)
    tb.wait()                       # wait for it to finish


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
	pass
