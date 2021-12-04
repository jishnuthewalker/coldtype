from dataclasses import dataclass
from coldtype.interpolation import lerp, interp_dict
from coldtype.pens.draftingpen import DraftingPen
from coldtype.time.easing import ease, ez, applyRange
from copy import copy
import math


class Timing():
    def __init__(self, t, loop_t, loop, easefn):
        self.t = t
        self.loop_t = loop_t
        self.loop = loop
        self.loop_phase = int(loop%2 != 0)
        self.e, self.s = self.ease(easefn)
    
    def ease(self, easefn):
        easer = easefn
        if not isinstance(easer, str) and not hasattr(easer, "value") and not type(easefn).__name__ == "Glyph":
            try:
                iter(easefn) # is-iterable
                if len(easefn) > self.loop:
                    easer = easefn[self.loop]
                elif len(easefn) == 2:
                    easer = easefn[self.loop % 2]
                elif len(easefn) == 1:
                    easer = easefn[0]
                else:
                    easer = easefn[0]
            except TypeError:
                print("failed")
                pass
        v, tangent = ease(easer, self.loop_t)
        return min(1, max(0, v)), tangent


class Timeable():
    """
    Abstract base class for anything with a concept of `start` and `end`/`duration`

    Implements additional methods to make it easier to work with time-based concepts
    """
    def __init__(self,
        start,
        end,
        index=0,
        name=None,
        data={},
        timeline=None,
        track=None,
        ):
        self.start = start
        self.end = end
        self.index = index
        self.idx = index
        self.i = index
        self.name = name
        self.feedback = 0
        self.data = data
        self.timeline = timeline
        self.track = track
    
    @property
    def duration(self):
        return self.end - self.start
    
    def __repr__(self):
        if self.name:
            return f"Timeable('{self.name}', {self.start}, {self.end} ({self.duration}))"
        else:
            return f"Timeable({self.start}, {self.end} ({self.duration}))"
    
    def delay(self, frames_delayed, feedback) -> 'Timeable':
        t = copy(self)
        t.start = t.start + frames_delayed
        t.end = t.end + frames_delayed
        t.feedback = feedback
        t.data = {}
        return t
    
    def retime(self, start=0, end=0, duration=-1):
        self.start = self.start + start
        self.end = self.end + end
        if duration > -1:
            self.end = self.start + duration
        return self
    
    def now(self, i):
        if self.start == self.end:
            return i == self.start
        else:
            return self.start <= i < self.end

    def _normalize_fi(self, fi):
        if hasattr(self, "timeline") and self.timeline:
            if self.end > self.timeline.duration and fi < self.start:
                return fi + self.timeline.duration
        return fi
    
    def e(self, fi, easefn="eeio", loops=1, rng=(0, 1), cyclic=True, to1=False, out1=False, **kwargs):
        if "r" in kwargs: rng = kwargs["r"]

        if not isinstance(easefn, str):
            loops = easefn
            easefn = "eeio"
        
        fi = self._normalize_fi(fi)
        t = self.progress(fi, loops=loops, easefn=easefn, cyclic=cyclic, to1=to1, out1=out1)
        e = t.e
        ra, rb = rng
        if ra > rb:
            e = 1 - e
            rb, ra = ra, rb
        return ra + e*(rb - ra)

    # def io(self, fi, length, ei="eei", eo="eei", negative=False):
    #     """
    #     Somewhat like ``progress()``, but can be used to fade in/out (hence the name (i)n/(o)ut)

    #     * ``length`` refers to the lenght of the ease, in frames
    #     * ``ei=`` takes the ease-in mnemonic
    #     * ``eo=`` takes the ease-out mnemonic
    #     """
    #     try:
    #         length_i, length_o = length
    #     except:
    #         length_i = length
    #         length_o = length
        
    #     fi = self._normalize_fi(fi)

    #     if fi < self.start:
    #         return 1
    #     if fi > self.end:
    #         return 0
    #     to_end = self.end - fi
    #     to_start = fi - self.start
    #     easefn = None
    #     in_end = False
    #     if to_end < length_o and eo:
    #         in_end = True
    #         v = 1-to_end/length_o
    #         easefn = eo
    #     elif to_start <= length_i and ei:
    #         v = 1-to_start/length_i
    #         easefn = ei
    #     else:
    #         v = 0
    #     if v == 0 or not easefn:
    #         return 0
    #     else:
    #         a, _ = ease(easefn, v)
    #         if negative and in_end:
    #             return -a
    #         else:
    #             return a
    
    # def io2(self, fi, length, easefn="eeio", negative=False):
    #     try:
    #         length_i, length_o = length
    #     except:
    #         length_i = length
    #         length_o = length
        
    #     if isinstance(length_i, float):
    #         length_i = int(self.duration*(length_i/2))
    #     if isinstance(length_o, float):
    #         length_o = int(self.duration*(length_o/2))
        
    #     if fi < self.start or fi > self.end:
    #         return 0
        
    #     try:
    #         ei, eo = easefn
    #     except ValueError:
    #         ei, eo = easefn, easefn

    #     to_end = self.end - fi
    #     to_start = fi - self.start
    #     easefn = None
    #     in_end = False

    #     if to_end < length_o and eo:
    #         in_end = True
    #         v = to_end/length_o
    #         easefn = eo
    #     elif to_start <= length_i and ei:
    #         v = to_start/length_i
    #         easefn = ei
    #     else:
    #         v = 1

    #     if v == 1 or not easefn:
    #         return 1
    #     else:
    #         a, _ = ease(easefn, v)
    #         return a
    #         if negative and in_end:
    #             return -a
    #         else:
    #             return a

    def _loop(self, t, times=1, cyclic=True, negative=False):
        lt = t*times*2
        ltf = math.floor(lt)
        ltc = math.ceil(lt)
        if False:
            if ltc % 2 != 0: # looping back
                lt = 1 - (ltc - lt)
            else: # looping forward
                lt = ltc - lt
        lt = lt - ltf
        if cyclic and ltf%2 == 1:
            if negative:
                lt = -lt
            else:
                lt = 1 - lt
        return lt, ltf
    
    def progress(self, i, loops=0, cyclic=True, negative=False, easefn="linear", to1=False, out1=True) -> Timing:
        """
        Given an easing function (``easefn=``), calculate the amount of progress as a Timing object

        ``easefn=`` takes a mnemonic as enumerated in :func:`coldtype.time.easing.ease`
        """
        if i < self.start:
            return Timing(0, 0, 0, easefn)
        if i > self.end:
            if out1:
                return Timing(1, 1, 0, easefn)
            else:
                return Timing(0, 0, 0, easefn)
        d = self.duration
        if to1:
            d = d - 1
        t = (i-self.start) / d
        if loops == 0:
            return Timing(t, t, 0, easefn)
        else:
            loop_t, loop_index = self._loop(t, times=loops, cyclic=cyclic, negative=negative)
            return Timing(t, loop_t, loop_index, easefn)
    
    def halfover(self, i):
        e = self.progress(i, to1=1).e
        return e >= 0.5
    
    #prg = progress

    def at(self, i) -> "Easeable":
        return Easeable(self, i)




class TimeableView(Timeable):
    def __init__(self, timeable, value, svalue, count, index, position, start, end):
        self.timeable = timeable
        self.value = value
        self.svalue = svalue
        self.count = count
        self.index = index
        self.position = position
        self.start = start
        self.end = end
        super().__init__(start, end)
    
    def ease(self, eo="eei", ei="eei"):
        return ease(eo, self.value)[0]
    
    def __repr__(self):
        return f"<TimeableView:{self.timeable}/>"


class TimeableSet():
    def __init__(self, timeables, name=None, start=-1, end=-1, data={}, flatten=False):
        self.timeables = sorted(timeables, key=lambda t: t.start)
        self.name = name
        self._start = start
        self._end = end
        self.data = data
        if flatten:
            self.timeables = self.flat_timeables()
    
    def flat_timeables(self):
        ts = []
        for t in self.timeables:
            if isinstance(t, TimeableSet):
                ts.extend(t.flat_timeables())
            else:
                ts.append(t)
        return ts

    def constrain(self, start, end):
        self._start = start
        self._end = end
    
    @property
    def start(self):
        if self._start > -1:
            return self._start
        _start = -1
        for t in self.timeables:
            ts = t.start
            if _start == -1:
                _start = ts
            elif ts < _start:
                _start = ts
        return _start

    @property
    def end(self):
        if self._end > -1:
            return self._end
        _end = -1
        for t in self.timeables:
            te = t.end
            if _end == -1:
                _end = te
            elif te > _end:
                _end = te
        return _end
    
    def __getitem__(self, index):
        return self.timeables[index]
    
    def current(self, frame):
        for idx, t in enumerate(self.flat_timeables()):
            t:Timeable
            if t.start <= frame and frame < t.end:
                return t
    
    def at(self, i) -> "Easeable":
        return Easeable(self.timeables, i)
    
    def _keyed(self, k):
        k = str(k)
        all = []
        if isinstance(k, str):
            for c in self.timeables:
                if c.name == k:
                    all.append(c)
        return all
    
    def k(self, *keys):
        if len(keys) > 1:
            es = [self.k(k) for k in keys]
            return TimeableSet(es, flatten=1)
        else:
            return TimeableSet(self._keyed(keys[0]), flatten=1)
    
    def ki(self, key, fi):
        """(k)eyed-at-(i)ndex"""

        if not isinstance(key, str):
            try:
                es = [self.ki(k, fi).t for k in key]
                return Easeable(es, fi)
            except TypeError:
                pass
        
        return Easeable(self._keyed(key), fi)

    def __repr__(self):
        return "<TimeableSet ({:s}){:04d}>".format(self.name if self.name else "?", len(self.timeables))
    

@dataclass
class EaseableTiming():
    t: float = 0
    i: int = -1


class Easeable():
    def __init__(self,
        t:Timeable,
        i:int
        ):
        self.t:Timeable = t
        self.i:int = i

        self._ts = False
        if not isinstance(t, Timeable):
            self._ts = True
    
    @property
    def autowrap(self):
        return False
    
    def __repr__(self) -> str:
        return f"<Easeable@{self.i}:{self.t}/>"
    
    def _normRange(self, rng, **kwargs):
        if "r" in kwargs:
            rng = kwargs["r"]
        if isinstance(rng, (int, float)):
            rng = (0, rng)
        return rng
    
    def _maxRange(self, rng, vs):
        if rng[1] > rng[0]:
            return max(vs)
        else:
            return min(vs)
    
    def index(self):
        if self._ts:
            return sum([self.i >= t.start for t in self.t]) - 1
        else:
            return int(self.i >= self.t.start) - 1
    
    def tv(self,
        loops=0,
        cyclic=True,
        to1=True,
        choose=max,
        wrap=None,
        find=False,
        clip=True
        ):
        if wrap is None and self.autowrap:
            wrap = True

        if self._ts:
            es = [Easeable(t, self.i).tv(loops, cyclic, to1).t for t in self.t]
            e = choose(es)
            if find is False:
                return EaseableTiming(e)
            else:
                return EaseableTiming(e, es.index(e))
                # chosen = [(i, 1 if x == e else 0) for i, x in enumerate(es)]
                # if e > 0:
                #     return EaseableTiming(e, chosen[-1][0])
                # else:
                #     return EaseableTiming(e, chosen[0][0])

        t, i = self.t, self.i
        if wrap:
            i = i % self.t.duration
        else:
            i = self.i

        if clip and i < t.start:
            return EaseableTiming(0)
        elif clip and i > t.end:
            if loops % 2 == 0:
                return EaseableTiming(1)
            else:
                return EaseableTiming(0)
        else:
            d = t.duration
            if to1:
                d = d - 1
            
            v = (i - t.start) / d
            if loops == 0:
                return EaseableTiming(max(0, min(1, v)) if clip else v)
            else:
                loop_t, loop_index = self.t._loop(v, times=loops, cyclic=cyclic, negative=False)
                return EaseableTiming(max(0, min(1, loop_t)) if clip else v)

    def e(self,
        easefn="eeio",
        loops=1,
        rng=(0, 1),
        on=None, # TODO?
        cyclic=True,
        to1=False,
        wrap=None,
        choose=max,
        find=False,
        **kwargs
        ):
        rng = self._normRange(rng, **kwargs)
        
        if (not isinstance(easefn, str)
            and not isinstance(easefn, DraftingPen)
            and not type(easefn).__name__ == "Glyph"):
            loops = easefn
            easefn = "eeio"
        
        tv = self.tv(loops, cyclic, to1, choose, wrap, find=True)
        
        ev = ez(tv.t, easefn, cyclic=cyclic, rng=rng)
        if find:
            return ev, tv.i
        else:
            return ev
    
    def interpDict(self, dicts, easefn, loops=0):
        v = self.tv(loops=loops).t
        vr = v*(len(dicts)-1)
        vf = math.floor(vr)
        v = vr-vf
        try:
            a, b = dicts[vf], dicts[vf+1]
            return interp_dict(ez(v, easefn), a, b)
        except IndexError:
            return dicts[vf]
    
    def io(self,
        length,
        easefn="eeio",
        negative=False,
        rng=(0, 1),
        **kwargs
        ):
        rng = self._normRange(rng, **kwargs)

        if self._ts:
            es = [Easeable(t, self.i).io(length, easefn, negative, rng) for t in self.t]
            return self._maxRange(rng, es)

        t = self.t
        try:
            length_i, length_o = length
        except:
            length_i = length
            length_o = length
        
        if isinstance(length_i, float):
            length_i = int(t.duration*(length_i/2))
        if isinstance(length_o, float):
            length_o = int(t.duration*(length_o/2))
        
        if self.i < t.start or self.i > t.end:
            return rng[0]
        
        try:
            ei, eo = easefn
        except ValueError:
            ei, eo = easefn, easefn

        to_end = t.end - self.i
        to_start = self.i - t.start
        easefn = None
        in_end = False

        if to_end < length_o and eo:
            in_end = True
            v = to_end/length_o
            easefn = eo
        elif to_start <= length_i and ei:
            v = to_start/length_i
            easefn = ei
        else:
            v = 1

        if v == 1 or not easefn:
            return rng[1]
        else:
            return ez(v, easefn, 0, False, rng)
            #a, _ = ease(easefn, v)
            #return a
            if negative and in_end:
                return -a
            else:
                return a
    
    def adsr(self,
        adsr=[5, 0, 0, 10],
        es=["eei", "qeio", "eeo"],
        rng=(0, 1),
        dv=None, # decay-value
        rs=False, # read-sustain
        find=False,
        **kwargs
        ):
        rng = self._normRange(rng, **kwargs)

        if self._ts:
            es = [Easeable(t, self.i).adsr(adsr, es, rng, dv, rs) for t in self.t]
            mx = self._maxRange(rng, es)
            if find:
                return mx, es.index(mx)
            else:
                return mx

        if len(adsr) == 2:
            d, s = 0, 0
            a, r = adsr
        elif len(adsr) == 3:
            d = 0
            a, s, r = adsr
        elif len(adsr) == 4:        
            a, d, s, r = adsr
        
        if rs:
            s = self.t.duration
        
        if len(es) == 2:
            de = "qeio"
            ae, re = es
        elif len(es) == 3:
            ae, de, re = es
        
        if dv is None:
            dv = rng[1]
            if d > 0:
                dv = lerp(rng[0], rng[1], 0.5)
        
        i, t = self.i, self.t
        end = t.start + d + s + r
        ds = t.start + d + s

        td = -1
        if t.timeline:
            td = t.timeline.duration

        if i > end and td > -1:
            i = i - td
        
        rv = rng[0]
        if td > -1 and end > td:
            if i < t.start-a:
                i = i + td
            rv = Easeable(Timeable(ds, end), i+td).e(re, 0, rng=(dv, rng[0]), to1=1)

        if i < t.start: # ATTACK
            s = t.start - a
            out = self._maxRange(rng, [rv, Easeable(Timeable(t.start-a, t.start), i).e(ae, 0, rng=rng, to1=0)])
        elif i >= t.start:
            if i == t.start:
                out = rng[1]
            if i >= ds: # RELEASE
                out = Easeable(Timeable(ds, end), i).e(re, 0, rng=(dv, rng[0]), to1=1)
            else:
                if i >= t.start + d: # SUSTAIN
                    out = dv
                else: # DECAY
                    out = Easeable(Timeable(t.start, ds), i).e(de, 0, rng=(rng[1], dv), to1=1)
        
        if find:
            return out, 0
        else:
            return out