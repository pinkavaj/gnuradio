#!/usr/bin/env python
#
# Copyright 2010,2011 Free Software Foundation, Inc.
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

from gnuradio import channels, gr
from gnuradio import blocks
from gnuradio import eng_notation
from gnuradio.eng_arg import eng_float, intx
from argparse import ArgumentParser

import random, math, sys

class my_top_block(gr.top_block):
    def __init__(self, ifile, ofile, args):
        gr.top_block.__init__(self)

        SNR = 10.0**(args.snr/10.0)
        frequency_offset = args.frequency_offset
        time_offset = args.time_offset
        phase_offset = args.phase_offset*(math.pi/180.0)

        # calculate noise voltage from SNR
        power_in_signal = abs(args.tx_amplitude)**2
        noise_power = power_in_signal/SNR
        noise_voltage = math.sqrt(noise_power)

        self.src = blocks.file_source(gr.sizeof_gr_complex, ifile)
        #self.throttle = blocks.throttle(gr.sizeof_gr_complex, args.sample_rate)

        self.channel = channels.channel_model(noise_voltage, frequency_offset,
                                            time_offset, noise_seed=-random.randint(0,100000))
        self.phase = blocks.multiply_const_cc(complex(math.cos(phase_offset),
                                                  math.sin(phase_offset)))
        self.snk = blocks.file_sink(gr.sizeof_gr_complex, ofile)

        self.connect(self.src, self.channel, self.phase, self.snk)
        

# /////////////////////////////////////////////////////////////////////////////
#                                   main
# /////////////////////////////////////////////////////////////////////////////

def main():
    parser = ArgumentParser(conflict_handler="resolve")
    parser.add_argument("-n", "--snr", type=eng_float, default=30,
                      help="set the SNR of the channel in dB [default=%(default)r]")
    parser.add_argument("--seed", action="store_true", default=False,
                      help="use a random seed for AWGN noise [default=%(default)r]")
    parser.add_argument("-f", "--frequency-offset", type=eng_float, default=0,
                      help="set frequency offset introduced by channel [default=%(default)r]")
    parser.add_argument("-t", "--time-offset", type=eng_float, default=1.0,
                      help="set timing offset between Tx and Rx [default=%(default)r]")
    parser.add_argument("-p", "--phase-offset", type=eng_float, default=0,
                      help="set phase offset (in degrees) between Tx and Rx [default=%(default)r]")
    parser.add_argument("-m", "--use-multipath", action="store_true", default=False,
                      help="Use a multipath channel [default=%(default)r]")
    parser.add_argument("--tx-amplitude", type=eng_float, default=1.0,
                      help="tell the simulator the signal amplitude [default=%(default)r]")
    parser.add_argument("input_file", metavar="INPUT-FILE", nargs=1)
    parser.add_argument("output_file", metavar="OUTPUT-FILE", nargs=1)

    args = parser.parse_args()

    ifile = args.input_file[0]
    ofile = args.output_file[0]

    # build the graph
    tb = my_top_block(ifile, ofile, args)

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
