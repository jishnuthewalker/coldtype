import unittest
from random import Random
from coldtype.geometry import Rect, Point
from coldtype.pens.runonpen import RunonPen

from coldtype.color import hsl, rgb
from coldtype.pens.drawablepen import DrawablePenMixin
from coldtype.renderer.reader import SourceReader
from coldtype.text.composer import StSt, Font
from coldtype.fx.chainable import Chainable

co = Font.Cacheable("assets/ColdtypeObviously-VF.ttf")
mutator = Font.Cacheable("assets/MutatorSans.ttf")

class TestRunonPen(unittest.TestCase):
    def test_gs(self):
        r = Rect(0, 0, 100, 100)
        dps = RunonPen()
        dp = (RunonPen()
            .define(r=r)
            .gs("$r↖ $r↗ $r↙|↘|65 ɜ"))
        self.assertEqual(len(dp.v.value), 4)
        self.assertEqual(dp.v.value[-2][-1][0], Point(100, 35))
        self.assertEqual(dp.v.value[-1][0], "endPath")
        self.assertEqual(dp.unended(), False)
        dps.append(RunonPen([dp]))
        self.assertEqual(len(dps.tree().splitlines()), 4)
        self.assertEqual(dps.tree().splitlines()[-1],
            " | - <®:RunonPen:RecordingPen(4mvs)>")
        
    def test_gs_arrowcluster(self):
        r = Rect(100, 100)
        dp = (RunonPen()
            .define(r=r)
            .gs("$r↖↗↘"))
        
        self.assertEqual(len(dp.v.value), 4)
        self.assertEqual(dp.v.value[0][-1][0], Point(0, 100).xy())
        self.assertEqual(dp.v.value[1][-1][0], Point(100, 100).xy())
        self.assertEqual(dp.v.value[2][-1][0], Point(100, 0).xy())
    
    def _test_gs_relative_moves(self):
        r = Rect(100, 100)
        dp = (RunonPen()
            .define(r=r)
            .gs("$r↖ ¬OX50OY-50 §OY-50"))
        
        self.assertEqual(len(dp.v.value), 4)
        self.assertEqual(dp.v.value[0][-1][0], Point(0, 100))
        self.assertEqual(dp.v.value[1][-1][0], Point(50, 50))
        self.assertEqual(dp.v.value[2][-1][0], Point(0, 50))
    
    def test_gss(self):
        """
        A rect passed to gs and gss should create the same value on the pen
        """
        dp1 = (RunonPen()
            .define(r=Rect(100, 100))
            .gss("$r"))
        
        dp2 = (RunonPen()
            .define(r=Rect(100, 100))
            .gs("$r"))
        
        self.assertEqual(dp1.v.value, dp2.v.value)
        
    def test_reverse(self):
        dp = (RunonPen()
            .define(r=Rect(100, 100))
            .gs("$r↖ $r↗ $r↘ ɜ"))
        p1 = dp.v.value[0][-1]
        p2 = dp.reverse().v.value[-2][-1]
        self.assertEqual(p1, p2)
    
    def test_transforms(self):
        dp = (RunonPen(Rect(100, 100))
            .data(frame=Rect(100, 100))
            .align(Rect(200, 200)))
        
        self.assertEqual(dp.data("frame").mxx, 150)
        self.assertEqual(dp.v.value[-2][-1][-1][0], 50)

        self.assertEqual(
            dp.copy().rotate(45).round().v.value,
            dp.copy().rotate(360+45).round().v.value)
        
        self.assertEqual(dp.copy().scale(2).ambit().w, 200)

    def test_pens_ambit(self):
        dps = (RunonPen([
                RunonPen(Rect(50, 50)),
                RunonPen(Rect(100, 100, 100, 100))])
                #.print(lambda x: x.tree())
                )
        ram = dps.ambit()
        self.assertEqual(ram, Rect(0, 0, 200, 200))

        moves = []
        dps.walk(lambda p, pos, _: moves.append([p, pos]))
        self.assertEqual(moves[0][0], dps)
        self.assertEqual(moves[0][1], -1)
        self.assertEqual(moves[1][1], 0)
    
    def test_remove_blanks(self):
        dps = (RunonPen([
            RunonPen(Rect(50, 50)),
            RunonPen()
        ]))
        self.assertEqual(len(dps), 2)
        dps.unblank()
        self.assertEqual(len(dps), 1)
    
    def test_collapse(self):
        r = RunonPen([
            RunonPen([RunonPen([RunonPen()])]),
            RunonPen([RunonPen()]),
        ])

        self.assertIsInstance(r[0], RunonPen)
        self.assertIsInstance(r[0][0], RunonPen)

        r.collapse()
        self.assertIsInstance(r[0], RunonPen)
        self.assertIsInstance(r[1], RunonPen)

        r = RunonPen([
            RunonPen([RunonPen([RunonPen()])]),
            RunonPen([RunonPen()]),
        ])

        r2 = r.copy().collapse()
        self.assertEqual(len(r), 2)

        self.assertIsInstance(r[0], RunonPen)
        self.assertIsInstance(r[0][0], RunonPen)

        self.assertIsInstance(r2[0], RunonPen)
        self.assertIsInstance(r2[1], RunonPen)
    
    def test_find(self):
        dps = RunonPen([
            RunonPen([RunonPen([RunonPen().tag("find-me").f(hsl(0.9))])]),
            RunonPen().tag("not-me"),
            RunonPen([RunonPen().tag("find-me").f(hsl(0.3))])])

        self.assertEqual(dps.find("find-me")[0].f().h/360, 0.9)
        self.assertAlmostEqual(dps.find("find-me")[1].f().h/360, 0.3)

    def test_cond(self):
        dps = (RunonPen([
            (RunonPen().cond(True,
                lambda p: p.f(rgb(1, 0, 0))))]))
        
        self.assertEqual(dps[0].f().r, 1)

        def _build(condition):
            return (RunonPen([
                (RunonPen().cond(condition,
                    lambda p: p.f(rgb(0, 0, 1)),
                    lambda p: p.f(rgb(1, 0, 0))))]))
        
        self.assertEqual(_build(True)[0].f().b, 1)
        self.assertEqual(_build(False)[0].f().r, 1)
    
    def test_alpha(self):
        dps = (RunonPen([
            (RunonPen([
                (RunonPen().alpha(0.5))
            ]).alpha(0.5))
        ]).alpha(0.25))

        def walker(p, pos, data):
            if pos == 0:
                self.assertEqual(data["alpha"], 0.0625)
            elif pos == 1 and data["depth"] == 0:
                self.assertEqual(data["alpha"], 0.25)
            elif pos == 1 and data["depth"] == 1:
                self.assertEqual(data["alpha"], 0.125)

        dps.walk(walker)
    
    def test_visibility(self):
        dps = (RunonPen([
            (RunonPen([
                (RunonPen().visible(1).tag("visible")),
                (RunonPen().visible(0).tag("invisible"))
            ]))
        ]))

        def walker(p, pos, data):
            nonlocal visible_pen_count
            if pos == 0:
                visible_pen_count += 1

        visible_pen_count = 0
        dps.walk(walker, visible_only=True)
        self.assertEqual(visible_pen_count, 1)

        visible_pen_count = 0
        dps.walk(walker, visible_only=False)
        self.assertEqual(visible_pen_count, 2)

        visible_pen_count = 0
        dps[0][0].visible(0)
        dps.walk(walker, visible_only=True)
        self.assertEqual(visible_pen_count, 0)
    
    def test_style(self):
        src = """
from coldtype import *

def two_styles(r):
    return (RunonPen()
        .oval(r.inset(50).square())
        .f(hsl(0.8))
        .attr("alt", fill=hsl(0.3)))

@renderable()
def no_style_set(r):
    return two_styles(r)

@renderable(style="alt")
def style_set(r):
    return two_styles(r)

def lattr_styles(r):
    return (RunonPen()
        .oval(r.inset(50).square())
        .f(hsl(0.5)).s(hsl(0.7)).sw(5)
        .lattr("alt", lambda p: p.f(hsl(0.7)).s(hsl(0.5)).sw(15)))

@renderable()
def lattr_no_style(r):
    return lattr_styles(r)

@renderable(style="alt")
def lattr_style_set(r):
    return lattr_styles(r)
"""

        sr = SourceReader(None, code=src)
        rs = sr.frame_results(0)
        sr.unlink()

        self.assertNotEqual(
            rs[0][-1].attr(rs[0][0].style, "fill"),
            rs[1][-1].attr(rs[1][0].style, "fill"))
        
        self.assertNotEqual(
            rs[2][-1].attr(rs[2][0].style, "fill"),
            rs[3][-1].attr(rs[3][0].style, "fill"))
        
        self.assertEqual(rs[2][-1].attr(rs[2][0].style, "strokeWidth"), 5)
        self.assertEqual(rs[3][-1].attr(rs[3][0].style, "strokeWidth"), 15)

        dpm = DrawablePenMixin()
        dpm.dat = rs[3][-1]
        attrs = [x for _, x in list(dpm.findStyledAttrs(rs[3][0].style))]
        self.assertEqual(len(attrs), 2)
        self.assertEqual(attrs[1][1].get("weight"), 15)

    def test_subsegmenting(self):
        f1 = Font.Cacheable("assets/ColdtypeObviously_BlackItalic.ufo")

        shape = (StSt("C", f1, 1000, wght=0.5)[0]
            .explode()[0])

        self.assertAlmostEqual(
            shape.length()/2,
            shape.copy().subsegment(0, 0.5).length(),
            delta=1)
        
        self.assertAlmostEqual(
            shape.length(),
            shape.copy().subsegment(0, 1).length(),
            delta=1)
        
        shape1 = (StSt("D", f1, 1000, wght=0.5)[0]
            .explode()[0])
        
        shape2 = shape1.copy().fully_close_path()

        self.assertLess(shape1.length(), shape2.length())

        self.assertAlmostEqual(
            shape2.length()/2,
            shape2.copy().subsegment(0, 0.5).length(),
            delta=1)
    
    def test_explode(self):
        r = Rect(1000, 500)
        
        o1 = (StSt("O", co, 500, wdth=1).pen())
        o2 = (StSt("O", co, 500, wdth=1)
            .pen()
            .explode()
            .index(1, lambda p: p.rotate(90))
            .implode().f(hsl(0.3)).align(r))
        
        self.assertEqual(
            o1.explode()[0].ambit().w,
            o2.explode()[0].ambit().w)

        self.assertAlmostEqual(
            o1.explode()[1].ambit().h,
            o2.explode()[1].ambit().w)
    
    def test_scaleToRect(self):
        r = Rect(1000, 500)
        dps = RunonPen([
            (StSt("SPACEFILLING", mutator, 50)
                .align(r)
                .f(hsl(0.8))
                .scaleToRect(r.inset(100, 100), False)),
            (StSt("SPACEFILLING", mutator, 50)
                .align(r)
                .f(hsl(0.5))
                .scaleToWidth(r.w-20)),
            (StSt("SPACEFILLING", mutator, 50)
                .align(r)
                .f(hsl(0.3))
                .scaleToHeight(r.h-50))])
        
        self.assertAlmostEqual(
            dps[0].ambit(th=1).w, r.inset(100).w)
        self.assertAlmostEqual(
            dps[0].ambit(tv=1).h, r.inset(100).h)
        self.assertAlmostEqual(
            dps[1].ambit(th=1).w, r.w-20)
        self.assertAlmostEqual(
            dps[2].ambit(tv=1).h, r.h-50)
        
        dps.picklejar(r)
    
    def test_distribute_and_track(self):
        dps = RunonPen()
        rnd = Random(0)
        r = Rect(1000, 500)

        for _ in range(0, 11):
            dps += (RunonPen()
                .rect(Rect(100, 100))
                .f(hsl(rnd.random(), s=0.6))
                .rotate(rnd.randint(-45, 45)))
        dps = (dps
            .distribute()
            .track(-50)
            .reverse()
            .understroke(s=0.2)
            .align(r)
            )
        
        self.assertEqual(len(dps), 11)
        self.assertEqual(dps.ambit(th=1).round().w, 830)
    
        dps.picklejar(r)
    
    def test_track_to_rect(self):
        r = Rect(1000, 500)
        text = (StSt("COLD", co, 300, wdth=0, r=1)
            .align(r)
            .track_to_rect(r.inset(50, 0), r=1))
        
        self.assertEqual(text[0].glyphName, "D")
        self.assertEqual(text[-1].ambit().round().x, 50)
        self.assertEqual(text[0].ambit().round().x, 883)
    
    def test_sample(self):
        r = Rect(1000, 500)
        dp = (RunonPen()
            .define(r=r)
            .gs("$r↖ $r↗ $r↙|↘|65 ɜ"))
        # dp = (RunonPen()
        #     .define(r=r)
        #     .gs("$r↙ $r↗ ɜ")
        #     .fssw(None, 0, 5))
        dp.picklejar(r)
    
    def test_distribute_oval(self):
        r = Rect(1000, 500)
        txt = (StSt("COLDTYPE "*7, co, 64,
            tu=-50, r=1, ro=1)
            .distribute_on_path(RunonPen()
                .oval(r.inset(50))
                .reverse()
                .repeat())
            .understroke(s=0, sw=5))
        
        txt.picklejar(r)

        self.assertEqual(len(txt), 62)
        
        x, y = txt[-1].ambit().xy()
        self.assertAlmostEqual(x, 500, 0)
        self.assertAlmostEqual(y, 50, 0)
    
    def _test_distribute_path_center(self):
        r = Rect(1000, 500)
        lockup = (RunonPen()
            .define(
                r=r,
                nx=100,
                a="$rIX100SY+200")
            .gs("$a↙ $a↑|$a↖OX+$nx|65 $a↘|$a↗OX-$nx|65 ɜ")
            .fssw(-1, 0, 4)
            # .append(lambda ps: StSt(
            #     "Coldtype Cdelopty".upper(),
            #     co, 100, wdth=0.5)
            #     .pens()
            #     .distribute_on_path(ps[0], center=-5)
            #     .f(hsl(0.9)))
            # .align(r)
            )
        
        lockup.picklejar(r)
        
        x, y = lockup[1][10].ambit().xy()
        self.assertAlmostEqual(x, 534, 0)
        self.assertAlmostEqual(y, 362, 0)

        x, y, w, h = lockup[1].ambit()
        self.assertAlmostEqual(x, 196, 0)
        self.assertAlmostEqual(y, 236, 0)
        self.assertAlmostEqual(w, 643, 0)
        self.assertAlmostEqual(h, 202, 0)
    
    def test_distribute_path_lines(self):
        r = Rect(1080, 1080).inset(200)
        p = (RunonPen()
            .moveTo(r.psw)
            .lineTo(r.pn)
            .lineTo(r.pse)
            .endPath())

        lockup = (StSt("COLDTYPE",
            Font.MutatorSans(), 220, wght=.4, wdth=0.5)
            .distribute_on_path(p)
            .align(r, tv=1, th=1)
            .f(0))
        
        lockup.picklejar(Rect(1080, 1080))

        x, y = lockup[3].ambit().xy()
        self.assertEqual(lockup[3].glyphName, "D")
        self.assertAlmostEqual(x, 454, 0)
        self.assertAlmostEqual(y, 690, 0)

        x, y = lockup[-1].ambit().xy()
        self.assertEqual(lockup[-1].glyphName, "E")
        self.assertAlmostEqual(x, 792, 0)
        self.assertAlmostEqual(y, 312, 0)
    
    def test_stack(self):
        r = Rect(540, 540)
        sr = Rect(100, 100)

        res = (RunonPen([
            (RunonPen()
                .oval(sr)
                .f(hsl(0.5))
                .tag("A")),
            (RunonPen()
                .oval(sr)
                .f(hsl(0.7))
                .tag("B")),
            (RunonPen()
                .oval(sr)
                .f(hsl(0.9))
                .tag("C"))])
            .stack(10))
        
        res.picklejar(r)

        self.assertEqual(res.find_("C").ambit().y, 0)
        self.assertEqual(res.find_("B").ambit().y, 110)
        self.assertEqual(res.find_("A").ambit().y, 220)
    
    def test_stack_and_lead(self):
        r = Rect(540, 540)
        sr = Rect(100, 100)

        res = (RunonPen([
            (RunonPen()
                .oval(sr)
                .f(hsl(0.5))
                .tag("A")),
            (RunonPen()
                .oval(sr)
                .f(hsl(0.7))
                .tag("B")),
            (RunonPen()
                .oval(sr)
                .f(hsl(0.9))
                .tag("C"))])
            .stack(10)
            .lead(10))
        
        res.picklejar(r)

        self.assertEqual(res.find_("C").ambit().y, 0)
        self.assertEqual(res.find_("B").ambit().y, 120)
        self.assertEqual(res.find_("A").ambit().y, 240)
    
    def test_chain(self):
        def c1(a):
            def _c1(p:RunonPen):
                return [a]
            return Chainable(_c1)
        
        def c2(a):
            def _c2(p:RunonPen):
                p.data(hello=a)
                return None
            return Chainable(_c2)
        
        p1 = RunonPen() | c1(1)
        self.assertEqual(p1, [1])

        p2 = RunonPen() | c2("chain")
        self.assertTrue(isinstance(p2, RunonPen))
        self.assertEqual(p2.data("hello"), "chain")


if __name__ == "__main__":
    unittest.main()