# -*- coding: utf-8 -*-
"""MotoGymkhana Track Generator MVP. Python 3.10+, standard library only."""
from __future__ import annotations
import math, random, tkinter as tk
from tkinter import ttk, messagebox, filedialog
from dataclasses import dataclass

@dataclass
class Cone:
    x: float; y: float; kind: str; label: str = ""
@dataclass
class Track:
    width: float; height: float; cones: list[Cone]; route: list[tuple[float,float]]; seed: int

class TrackGenerator:
    def __init__(self, w, h, count, difficulty, seed=None):
        self.w,self.h,self.count,self.difficulty=w,h,count,difficulty
        self.seed=seed if seed is not None else random.randrange(1,10**9)
        self.rng=random.Random(self.seed)
    def generate(self):
        if self.w < 12 or self.h < 16: raise ValueError('Минимальный размер площадки — 12 × 16 м.')
        if self.count < 2 or self.count > 200: raise ValueError('Количество конусов: от 2 до 200.')
        margin=2.0; usable_w=self.w-2*margin; usable_h=self.h-2*margin
        rows=max(2,min(6,int(usable_h//6)+1))
        if usable_h/(rows-1)<4: rows=max(2,int(usable_h//4)+1)
        row_gap=usable_h/(rows-1); xs=[margin+usable_w*f for f in (.12,.38,.62,.88)]
        candidates=[]
        for i in range(rows):
            y=margin+i*row_gap
            for j,x in enumerate(xs if i%2==0 else xs[::-1]):
                yy=max(margin,min(self.h-margin,y+(.7 if j%2 else -.7)))
                candidates.append((x,yy))
        chosen=[]
        # Place slalom cones first; each selected pair is at least 4 m apart.
        for x,y in candidates:
            if len(chosen)>=self.count: break
            if all(math.dist((x,y),(c.x,c.y))>=4 for c in chosen):
                chosen.append(Cone(x,y,'red' if len(chosen)%2==0 else 'blue','Змейка'))
        attempts=0
        while len(chosen)<self.count and attempts<10000:
            attempts+=1; mode=self.rng.choice(['right','left','spin_r','spin_l','mirror'])
            if mode=='mirror' and self.count-len(chosen)<2: mode=self.rng.choice(['right','left','spin_r','spin_l'])
            x=self.rng.uniform(margin+1,self.w-margin-1); y=self.rng.uniform(margin+1,self.h-margin-1)
            if mode=='mirror':
                ang=self.rng.choice([0,math.pi/2]); dx,dy=1.75*math.cos(ang),1.75*math.sin(ang)
                pair=[(x-dx,y-dy),(x+dx,y+dy)]
                if not all(margin<=px<=self.w-margin and margin<=py<=self.h-margin for px,py in pair): continue
                if any(math.dist(p,(c.x,c.y))<2 for p in pair for c in chosen): continue
                chosen.extend([Cone(*pair[0],'yellow','Зеркало'),Cone(*pair[1],'yellow','Зеркало')])
            else:
                if any(math.dist((x,y),(c.x,c.y))<4 for c in chosen): continue
                kind,label={'right':('red','Правый поворот'),'left':('blue','Левый поворот'),
                    'spin_r':('red_yellow','Вращение 360° вправо'),'spin_l':('blue_yellow','Вращение 360° влево')}[mode]
                chosen.append(Cone(x,y,kind,label))
        if len(chosen)<self.count: raise ValueError('Не удалось разместить столько конусов. Увеличьте площадку или уменьшите количество.')
        chosen=chosen[:self.count]
        # Nearest-neighbour order for a suggested connecting line.
        remaining=chosen[:]; cur=min(remaining,key=lambda c:(c.x,-c.y)); ordered=[cur]; remaining.remove(cur)
        while remaining:
            nxt=min(remaining,key=lambda c:math.dist((c.x,c.y),(cur.x,cur.y))); ordered.append(nxt); remaining.remove(nxt); cur=nxt
        return Track(self.w,self.h,chosen,[(c.x,c.y) for c in ordered],self.seed)

class App(tk.Tk):
    def __init__(self):
        super().__init__(); self.title('Генератор трасс powered by Motogymkhana Glazov'); self.geometry('1180x780'); self.minsize(900,620)
        self.track=None; self.configure(bg='#f1f3f5'); self.build(); self.generate()
    def build(self):
        top=ttk.Frame(self,padding=12); top.pack(fill=tk.X)
        ttk.Label(top,text='Генератор трасс для мотоджимханы',font=('Segoe UI',17,'bold')).pack(anchor='w')
        ttk.Label(top,text='Схема сверху • размеры в метрах • ограничения по расстояниям').pack(anchor='w',pady=(2,8))
        box=ttk.LabelFrame(top,text='Параметры',padding=8); box.pack(fill=tk.X)
        self.w=tk.StringVar(value='30'); self.h=tk.StringVar(value='50'); self.n=tk.StringVar(value='20'); self.diff=tk.StringVar(value='Средний'); self.seed=tk.StringVar()
        for label,var,width in [('Ширина, м',self.w,7),('Длина, м',self.h,7),('Количество конусов',self.n,8)]:
            ttk.Label(box,text=label).pack(side=tk.LEFT,padx=(0,4)); ttk.Entry(box,textvariable=var,width=width).pack(side=tk.LEFT,padx=(0,12))
        ttk.Label(box,text='Сложность').pack(side=tk.LEFT,padx=(0,4)); ttk.Combobox(box,textvariable=self.diff,values=['Начальный','Средний','Продвинутый'],state='readonly',width=13).pack(side=tk.LEFT,padx=(0,12))
        ttk.Label(box,text='Seed').pack(side=tk.LEFT,padx=(0,4)); ttk.Entry(box,textvariable=self.seed,width=10).pack(side=tk.LEFT,padx=(0,12))
        ttk.Button(box,text='Сгенерировать трассу',command=self.generate).pack(side=tk.LEFT,padx=4)
        ttk.Button(box,text='Сохранить схему',command=self.save).pack(side=tk.LEFT,padx=4)
        body=ttk.Frame(self,padding=(12,0,12,12)); body.pack(fill=tk.BOTH,expand=True)
        self.canvas=tk.Canvas(body,bg='white',highlightthickness=1,highlightbackground='#cbd2d9'); self.canvas.pack(side=tk.LEFT,fill=tk.BOTH,expand=True); self.canvas.bind('<Configure>',lambda e:self.draw())
        side=ttk.Frame(body,width=275); side.pack(side=tk.RIGHT,fill=tk.Y,padx=(12,0)); side.pack_propagate(False)
        ttk.Label(side,text='Легенда',font=('Segoe UI',12,'bold')).pack(anchor='w',pady=(4,8))
        for col,txt,stripe in [('#d62728','Красный — правый поворот',False),('#1769d2','Синий — левый поворот',False),('#d62728','Красный + жёлтая полоса — 360° вправо',True),('#1769d2','Синий + жёлтая полоса — 360° влево',True),('#f2c500','Два жёлтых — зеркало (3–4 м)',False)]:
            row=ttk.Frame(side); row.pack(fill=tk.X,pady=3); sw=tk.Canvas(row,width=26,height=24,bg='#f1f3f5',highlightthickness=0); sw.pack(side=tk.LEFT,padx=(0,6)); sw.create_oval(4,4,22,22,fill=col,outline='#222')
            if stripe: sw.create_line(5,13,21,13,fill='#ffe64a',width=4)
            ttk.Label(row,text=txt,wraplength=220).pack(side=tk.LEFT,fill=tk.X)
        ttk.Separator(side).pack(fill=tk.X,pady=10); ttk.Label(side,text='Сводка',font=('Segoe UI',12,'bold')).pack(anchor='w')
        self.info=tk.Text(side,height=16,wrap=tk.WORD,font=('Segoe UI',9),relief=tk.FLAT,bg='#f1f3f5'); self.info.pack(fill=tk.BOTH,expand=True,pady=6); self.info.configure(state=tk.DISABLED)
        ttk.Label(side,text='Схема предварительная: перед заездом проверьте проходимость, радиусы поворотов и безопасность площадки.',wraplength=255,foreground='#8b3a00').pack(anchor='w')
        self.status=tk.StringVar(value='Готов к генерации'); ttk.Label(self,textvariable=self.status,relief=tk.SUNKEN,anchor='w',padding=5).pack(side=tk.BOTTOM,fill=tk.X)
    def generate(self):
        try:
            w=float(self.w.get().replace(',','.')); h=float(self.h.get().replace(',','.')); n=int(self.n.get()); seed=int(self.seed.get()) if self.seed.get().strip() else None
            self.track=TrackGenerator(w,h,n,self.diff.get(),seed).generate(); self.draw(); self.summary()
            self.status.set(f'Готово: {w:g} × {h:g} м • {n} конусов • seed {self.track.seed}')
        except Exception as e: messagebox.showerror('Не удалось сгенерировать трассу',str(e))
    def coords(self):
        if not self.track:return None
        cw=max(100,self.canvas.winfo_width()); ch=max(100,self.canvas.winfo_height()); pad=42
        s=min((cw-2*pad)/self.track.width,(ch-2*pad)/self.track.height); return s,(cw-self.track.width*s)/2,(ch-self.track.height*s)/2
    def draw(self):
        self.canvas.delete('all')
        if not self.track:return
        v=self.coords()
        if not v:return
        s,ox,oy=v; x1=ox+self.track.width*s; y1=oy+self.track.height*s
        self.canvas.create_rectangle(ox,oy,x1,y1,outline='#252a30',width=2,fill='#fbfcfd')
        for m in range(1,int(self.track.width)): self.canvas.create_line(ox+m*s,oy,ox+m*s,y1,fill='#edf0f2')
        for m in range(1,int(self.track.height)): self.canvas.create_line(ox,oy+m*s,x1,oy+m*s,fill='#edf0f2')
        self.canvas.create_text((ox+x1)/2,max(12,oy-17),text=f'{self.track.width:g} м',font=('Segoe UI',10,'bold'))
        self.canvas.create_text(max(12,ox-22),(oy+y1)/2,text=f'{self.track.height:g} м',angle=90,font=('Segoe UI',10,'bold'))
        pts=[]
        for x,y in self.track.route: pts += [ox+x*s,oy+y*s]
        if len(pts)>=4:self.canvas.create_line(*pts,fill='#8b949e',width=2,dash=(5,4),arrow=tk.LAST)
        r=max(5,min(10,s*.38))
        for i,c in enumerate(self.track.cones,1):
            x,y=ox+c.x*s,oy+c.y*s; color={'red':'#d62728','blue':'#1769d2','red_yellow':'#d62728','blue_yellow':'#1769d2','yellow':'#f2c500'}[c.kind]
            self.canvas.create_oval(x-r,y-r,x+r,y+r,fill=color,outline='#171717',width=1.4)
            if c.kind in ('red_yellow','blue_yellow'):self.canvas.create_line(x-r*.72,y,x+r*.72,y,fill='#ffe64a',width=max(2,r*.55))
            self.canvas.create_text(x+r+3,y-r-3,text=str(i),anchor='sw',fill='#333',font=('Segoe UI',8,'bold'))
        self.canvas.create_text(ox+5,y1+14,text='Пунктир — рекомендованный порядок, не физическая модель траектории',anchor='w',fill='#666',font=('Segoe UI',8))
    def summary(self):
        c={}
        for cone in self.track.cones:c[cone.kind]=c.get(cone.kind,0)+1
        lines=[f'Площадка: {self.track.width:g} × {self.track.height:g} м',f'Конусов: {len(self.track.cones)}',f'Seed: {self.track.seed}','',f'Правые повороты: {c.get("red",0)}',f'Левые повороты: {c.get("blue",0)}',f'Вращения вправо: {c.get("red_yellow",0)}',f'Вращения влево: {c.get("blue_yellow",0)}',f'Жёлтые конусы зеркала: {c.get("yellow",0)}','','Ограничения:','• конусы внутри площадки','• точки змейки разнесены минимум на 4 м','• зеркальная пара — 3,5 м','','Важно: автоматически построенная схема требует проверки инструктором.']
        self.info.configure(state=tk.NORMAL); self.info.delete('1.0',tk.END); self.info.insert('1.0','\n'.join(lines)); self.info.configure(state=tk.DISABLED)
    def save(self):
        if not self.track:return
        path=filedialog.asksaveasfilename(title='Сохранить схему',defaultextension='.ps',filetypes=[('PostScript (*.ps)','*.ps')])
        if path:
            try:self.canvas.postscript(file=path,colormode='color'); self.status.set('Сохранено: '+path+' (PS; можно конвертировать в PNG/PDF)')
            except Exception as e:messagebox.showerror('Ошибка сохранения',str(e))

if __name__=='__main__': App().mainloop()
