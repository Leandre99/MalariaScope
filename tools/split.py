"""Which downloaded patients tune the detector and which are held out.

Held-out patients are never used for tuning: the accuracy screen and the
sample slide only use them, so the reported numbers are honest.
"""
TUNING = ["TF102_234", "TF15_C87P48", "TF19_C94P55", "TF35_Sc521", "TF49_CW3", "TF86_BD2_93"]
HELD_OUT = ["TF63_CS25", "TF31_Sc440", "TF45_UW18", "TF7_C49P10"]
SAMPLE_PATIENT = "TF63_CS25"   # held out, 20 fields, 221 WBC, 839 parasites
