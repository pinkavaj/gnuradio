#!/usr/bin/env python
#
# Copyright 2005,2006,2009,2011,2013 Free Software Foundation, Inc.
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
from gnuradio import blocks
from gnuradio import filter
from gnuradio import eng_notation
from gnuradio.eng_arg import eng_float, intx
from argparse import ArgumentParser

from gnuradio import blocks
from gnuradio import digital
from gnuradio import vocoder

import random
import struct
import sys

# from current dir
from receive_path import receive_path
from uhd_interface import uhd_receiver

#import os
#print os.getpid()
#raw_input('Attach and press enter')


class audio_tx(gr.hier_block2):
    def __init__(self, audio_output_dev):
	gr.hier_block2.__init__(self, "audio_tx",
				gr.io_signature(0, 0, 0), # Input signature
				gr.io_signature(0, 0, 0)) # Output signature
				
        self.sample_rate = sample_rate = 8000
        self.packet_src = blocks.message_source(33)
        voice_decoder = vocoder.gsm_fr_decode_ps()
        s2f = blocks.short_to_float()
        sink_scale = blocks.multiply_const_ff(1.0/32767.)
        audio_sink = audio.sink(sample_rate, audio_output_dev)
        self.connect(self.packet_src, voice_decoder, s2f, sink_scale, audio_sink)
        
    def msgq(self):
        return self.packet_src.msgq()


class my_top_block(gr.top_block):
    def __init__(self, demod_class, rx_callback, options):
        gr.top_block.__init__(self)
        self.rxpath = receive_path(demod_class, rx_callback, options)
        self.audio_tx = audio_tx(args.audio_output)

        if(args.rx_freq is not None):
            self.source = uhd_receiver(args.args, args.bitrate,
                                       args.samples_per_symbol,
                                       args.rx_freq, args.rx_gain,
                                       args.antenna, args.verbose)
            args.samples_per_symbol = self.source._sps

            audio_rate = self.audio_tx.sample_rate
            usrp_rate = self.source.get_sample_rate()
            rrate = audio_rate / usrp_rate
            self.resampler = filter.pfb.arb_resampler_ccf(rrate)
            
            self.connect(self.source, self.resampler, self.rxpath)

        elif(args.from_file is not None):
            self.thr = blocks.throttle(gr.sizeof_gr_complex, args.bitrate)
            self.source = blocks.file_source(gr.sizeof_gr_complex, args.from_file)
            self.connect(self.source, self.thr, self.rxpath)

        else:
            self.thr = blocks.throttle(gr.sizeof_gr_complex, 1e6)
            self.source = blocks.null_source(gr.sizeof_gr_complex)
            self.connect(self.source, self.thr, self.rxpath)

	self.connect(self.audio_tx)        

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
        n_rcvd += 1
        if ok:
            n_right += 1

        tb.audio_tx.msgq().insert_tail(gr.message_from_string(payload))
        
        print "ok = %r  n_rcvd = %4d  n_right = %4d" % (
            ok, n_rcvd, n_right)

    demods = digital.modulation_utils.type_1_demods()

    # Create Options Parser:
    parser = ArgumentParser(conflict_handler="resolve")
    expert_grp = parser.add_argument_group("Expert")

    parser.add_argument("-m", "--modulation", choices=demods.keys(),
                      default='gmsk',
                      help="Select modulation from: %s [default=%%(default)r]"
                            % (', '.join(demods.keys()),))
    parser.add_argument("-O", "--audio-output", default="",
                      help="pcm output device name.  E.g., hw:0,0 or /dev/dsp")
    parser.add_argument("--from-file",
                      help="input file of samples to demod")
    receive_path.add_arguments(parser, expert_grp)
    uhd_receiver.add_arguments(parser)

    for mod in demods.values():
        mod.add_arguments(expert_grp)

    parser.set_defaults(bitrate=50e3)  # override default bitrate default
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

    tb.run()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
