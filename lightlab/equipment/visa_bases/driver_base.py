from abc import ABC, abstractmethod


class InstrumentSessionBase(ABC):
    ''' Base class for Instrument sessions, to be inherited and specialized
    by VISAObject and PrologixGPIBObject'''

    @abstractmethod
    def spoll(self):
        pass

    @abstractmethod
    def LLO(self):
        pass

    @abstractmethod
    def LOC(self):
        pass

    @abstractmethod
    def open(self):
        pass

    @abstractmethod
    def close(self):
        pass

    @abstractmethod
    def write(self):
        pass

    @abstractmethod
    def query(self):
        pass

    @abstractmethod
    def clear(self):
        pass

    @abstractmethod
    def query_raw_binary(self):
        pass

    def instrID(self):
        r"""Returns the \*IDN? string"""
        return self.query('*IDN?')

    @property
    @abstractmethod
    def timeout(self):
        pass

    @timeout.setter
    @abstractmethod
    def termination(self, newTimeout):
        pass
