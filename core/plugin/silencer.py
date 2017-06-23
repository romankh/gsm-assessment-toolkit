import os


class Silencer(object):
    def __enter__(self):
        # silence rtl_sdr output:
        # open 2 fds
        self.null_fds = [os.open(os.devnull, os.O_RDWR) for x in xrange(2)]
        # # save the current file descriptors to a tuple
        self.save = os.dup(1), os.dup(2)
        # # put /dev/null fds on 1 and 2
        os.dup2(self.null_fds[0], 1)
        os.dup2(self.null_fds[1], 2)

    def __exit__(self, type, value, traceback):
        # restore file descriptors so we can print the results
        os.dup2(self.save[0], 1)
        os.dup2(self.save[1], 2)
        # close the temporary fds
        os.close(self.null_fds[0])
        os.close(self.null_fds[1])

    def write(self, x): pass
