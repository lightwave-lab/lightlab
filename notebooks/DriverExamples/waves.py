from lightlab.util.data import Waveform
import numpy as np

def triangle_wave2(t, period, t_start, amplitude=1, offset=0, t_end=None):
    t_norm = ((t - t_start) / period) % 1  # time normalized by period. 0 - start, 0.5 - peak, 1 - end
    rising = (t_norm < 0.5)
    falling = (t_norm >= 0.5)
    triangle = t_norm * (rising * 2 - falling * 2) * amplitude + (2.0 * falling) * amplitude - np.full_like(t_norm, amplitude * 0.5 - offset)  
    triangle *= (t >= t_start)
    
    # limit the triangle until a certain t_end
    if t_end is not None:
        triangle *= (t < t_end)
    return Waveform(t, triangle)

def triangle_wave(t, period, t_start, t_end=None):
    return triangle_wave2(t, period, t_start, amplitude=1, offset=0.5, t_end=t_end)

def FM_sine_wave(t, t_start, f_start, df_dt):
    ordi = np.sin(2 * np.pi * (f_start + df_dt * (t - t_start)) * t)
    return Waveform(t, ordi)