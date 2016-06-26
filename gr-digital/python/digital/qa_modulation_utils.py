import modulation_utils
from argparse import ArgumentParser
from gnuradio import gr_unittest


class TestModulationUtils(gr_unittest.TestCase):
    def test_extract_kwargs_from_args1(self):
        def test_fun1(arg1, arg2=None):
            pass
        parser = ArgumentParser()
        parser.add_argument('--arg1')
        parser.add_argument('--arg2')
        cmd_args = ['--arg1', 'val1']
        args = parser.parse_args(cmd_args)
        d = modulation_utils.extract_kwargs_from_args(test_fun1, [], args)
        self.assertEqual({'arg1': 'val1'}, d)

    def test_extract_kwargs_from_args2(self):
        def test_fun1(arg1, arg2=None):
            pass
        parser = ArgumentParser()
        parser.add_argument('--arg1')
        parser.add_argument('--arg2')
        parser.add_argument('--arg3')
        cmd_args = ['--arg1', 'val1', '--arg2', 'val2', '--arg3', 'val3']
        args = parser.parse_args(cmd_args)
        d = modulation_utils.extract_kwargs_from_args(test_fun1, ['arg2'], args)
        self.assertEqual({'arg1': 'val1'}, d)

    def test_extract_kwargs_from_args3(self):
        def test_fun1(arg1, arg2=None):
            pass
        parser = ArgumentParser()
        parser.add_argument('--arg1')
        parser.add_argument('--arg2')
        parser.add_argument('--arg3')
        cmd_args = ['--arg1', 'val1', '--arg2', 'val2', '--arg3', 'val3']
        args = parser.parse_args(cmd_args)
        d = modulation_utils.extract_kwargs_from_args(test_fun1, [], args)
        self.assertEqual({'arg1': 'val1', 'arg2': 'val2'}, d)

if __name__ == '__main__':
    gr_unittest.run(TestModulationUtils, "modulation_utils.xml")
