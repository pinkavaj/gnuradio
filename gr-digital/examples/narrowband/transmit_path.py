#
# Copyright 2005-2007,2011 Free Software Foundation, Inc.
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

from argparse import ArgumentError
from gnuradio import gr
from gnuradio import eng_notation
from gnuradio import blocks
from gnuradio import digital
from gnuradio.eng_arg import eng_float

import copy
import sys

# /////////////////////////////////////////////////////////////////////////////
#                              transmit path
# /////////////////////////////////////////////////////////////////////////////

class transmit_path(gr.hier_block2):
    def __init__(self, modulator_class, args):
        '''
        See below for what args should hold
        '''
	gr.hier_block2.__init__(self, "transmit_path",
				gr.io_signature(0,0,0),
				gr.io_signature(1,1,gr.sizeof_gr_complex))
        
        args = copy.copy(args)    # make a copy so we can destructively modify

        self._verbose      = args.verbose
        self._tx_amplitude = args.tx_amplitude   # digital amplitude sent to USRP
        self._bitrate      = args.bitrate        # desired bit rate
        self._modulator_class = modulator_class     # the modulator_class we are using

        # Get mod_kwargs
        mod_kwargs = self._modulator_class.extract_kwargs_from_args(args)
        
        # transmitter
	self.modulator = self._modulator_class(**mod_kwargs)
        
        self.packet_transmitter = \
            digital.mod_pkts(self.modulator,
                             access_code=None,
                             msgq_limit=4,
                             pad_for_usrp=True)

        self.amp = blocks.multiply_const_cc(1)
        self.set_tx_amplitude(self._tx_amplitude)

        # Display some information about the setup
        if self._verbose:
            self._print_verbage()

        # Connect components in the flowgraph
        self.connect(self.packet_transmitter, self.amp, self)

    def set_tx_amplitude(self, ampl):
        """
        Sets the transmit amplitude sent to the USRP in volts
        
        Args:
            : ampl 0 <= ampl < 1.
        """
        self._tx_amplitude = max(0.0, min(ampl, 1))
        self.amp.set_k(self._tx_amplitude)
        
    def send_pkt(self, payload='', eof=False):
        """
        Calls the transmitter method to send a packet
        """
        return self.packet_transmitter.send_pkt(payload, eof)
        
    def bitrate(self):
        return self._bitrate

    def samples_per_symbol(self):
        return self.modulator._samples_per_symbol

    def differential(self):
        return self.modulator._differential

    @staticmethod
    def add_arguments(normal, expert):
        """
        Adds transmitter-specific args to the Options Parser
        """
        try:
            normal.add_argument("-r", "--bitrate", type=eng_float,
                              default=100e3,
                              help="specify bitrate [default=%(default)r].")
        except ArgumentError:
            pass
        normal.add_argument("--tx-amplitude", type=eng_float,
                          default=0.250, metavar="AMPL",
                          help="set transmitter digital amplitude: 0 <= AMPL < 1 [default=%(default)r]")
        normal.add_argument("-v", "--verbose", action="store_true",
                          default=False)

        expert.add_argument("-S", "--samples-per-symbol", type=float,
                          default=2,
                          help="set samples/symbol [default=%(default)r]")
        expert.add_argument("--log", action="store_true",
                          default=False,
                          help="Log all parts of flow graph to file (CAUTION: lots of data)")

    def _print_verbage(self):
        """
        Prints information about the transmit path
        """
        print "Tx amplitude     %s"    % (self._tx_amplitude)
        print "modulation:      %s"    % (self._modulator_class.__name__)
        print "bitrate:         %sb/s" % (eng_notation.num_to_str(self._bitrate))
        print "samples/symbol:  %.4f"  % (self.samples_per_symbol())
        print "Differential:    %s"    % (self.differential())
