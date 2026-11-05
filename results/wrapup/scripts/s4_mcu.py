"""Study 4: the microcontroller comparison (DECISIONS S4.5). Arithmetic only; every datasheet figure carries its
source (the fetched PDF in prior_art/lookups/, logged in LOG.jsonl, with the table it was read from). Typical values
at 25 C. The workload: wake up, digitise 6 analog sensor values, compute a 6 x 5 linear classifier (+ bias) and its
argmax, go back to sleep. Also computed from repository files: Tortoise's die-only energy (H2-02), the time the host
is busy per classification (host_v2 C1 read time), and a lower bound on Tortoise's active area (channel area of every
TFT plus the capacitors at C_i = 0.70 uF/cm^2, from docs/rev10_1_nominal.cir; no routing, contacts or pads).
-> summary/s4_mcu.json"""
import json, pathlib, re

WU = pathlib.Path(__file__).resolve().parents[1]
REPO = WU.parents[1]
LK = "prior_art/lookups/"
MSP430 = dict(
    part="TI MSP430FR2433 (SLASE59F, rev. Dec 2019)", file=LK + "20261030T122833Z_url_msp430fr2433_datasheet.pdf",
    V=3.0,
    I_active_8MHz_RAM_uA=818.0,           # Table 5.4, IAM,RAM, 8 MHz, 3 V, 25 C
    I_active_8MHz_FRAM100_uA=625.0,       # Table 5.4, IAM,FRAM(100%), 8 MHz
    I_LPM0_8MHz_uA=342.0,                 # Table 5.6, ILPM0, 8 MHz, 3 V
    I_LPM0_1MHz_uA=166.0,                 # Table 5.6, ILPM0, 1 MHz, 3 V
    I_LPM3_VLO_uA=0.98,                   # Table 5.7, ILPM3,VLO, 3 V, 25 C
    I_LPM4_uA=0.49,                       # Table 5.7, ILPM4, 3 V, 25 C
    I_LPM45_uA=0.016,                     # Table 5.8, ILPM4.5 (excl. SVS), 3 V, 25 C
    t_wake_LPM3_us=10.0,                  # Table 5-3, tWAKE-UP LPM3
    t_wake_LPM45_us=1000.0,               # Table 5-3, tWAKE-UP LPM4.5 (SVSHE = 0)
    I_ADC_uA=207.0,                       # Table 5-20, IADC, 3 V, fADCCLK 5 MHz
    t_sample_us=2.0,                      # Table 5-21, tSample, 3 V (RS = 1 kOhm)
    t_convert_us=2.67,                    # Table 5-21, tCONVERT, 10-bit, internal oscillator (max of 2.18-2.67)
    f_MHz=8.0,
    package="DSBGA-24 (YQW) 2.29 mm x 2.34 mm",   # Section 1.3, Device Information
    package_mm2=2.29 * 2.34)
MSPM0 = dict(
    part="TI MSPM0L1306 (SLASEX0D, rev. Jan 2024)", file=LK + "20261030T122919Z_url_mspm0l1306_datasheet.pdf",
    V=3.3,
    I_run_32MHz_mA=2.3,                   # 7.5.1, IDDRUN, 32 MHz, CoreMark, flash
    I_standby_uA=1.0,                     # 7.5.2, IDDSTBY1, 25 C
    I_shutdown_uA=0.061,                  # 7.5.3, IDDSHDN, 25 C
    t_wake_standby_us=15.0,               # 7.8, tWAKE,STBY
    I_ADC_uA=454.0,                       # 7.12.1, I(ADC), 1 Msps, internal reference off
    t_conv_us=1.0,                        # 1 Msps operating point of the I(ADC) figure
    f_MHz=32.0,
    package="WQFN-16 (RTR) 3 mm x 2 mm",  # Table 5-1
    package_mm2=3.0 * 2.0)
CYCLES = dict(low=500, nominal=1000, high=3000)   # 6 normalisations + 30 MACs + 5 biases + argmax + loop/call overhead;
#   'high' = no hardware multiplier (software multiply). An ASSUMPTION, not measured; MSP430FR2433 has the MPY32
#   hardware multiplier (datasheet Section 6.10.9).


def msp430(cyc):
    d = MSP430
    P_act = d["I_active_8MHz_RAM_uA"] * 1e-6 * d["V"]
    e_wake = d["t_wake_LPM3_us"] * 1e-6 * P_act                                  # counted at the active current
    t_adc = 6 * (d["t_sample_us"] + d["t_convert_us"])
    e_adc = t_adc * 1e-6 * (d["I_ADC_uA"] + d["I_active_8MHz_RAM_uA"]) * 1e-6 * d["V"]   # CPU kept active (upper)
    e_cpu = cyc / (d["f_MHz"] * 1e6) * P_act
    return dict(wake_nJ=e_wake * 1e9, adc_nJ=e_adc * 1e9, compute_nJ=e_cpu * 1e9, total_nJ=(e_wake + e_adc + e_cpu) * 1e9,
                busy_us=d["t_wake_LPM3_us"] + t_adc + cyc / d["f_MHz"])


def mspm0(cyc):
    d = MSPM0
    P_act = d["I_run_32MHz_mA"] * 1e-3 * d["V"]
    e_wake = d["t_wake_standby_us"] * 1e-6 * P_act
    e_adc = 6 * d["t_conv_us"] * 1e-6 * (d["I_ADC_uA"] * 1e-6 + d["I_run_32MHz_mA"] * 1e-3) * d["V"]
    e_cpu = cyc / (d["f_MHz"] * 1e6) * P_act
    return dict(wake_nJ=e_wake * 1e9, adc_nJ=e_adc * 1e9, compute_nJ=e_cpu * 1e9, total_nJ=(e_wake + e_adc + e_cpu) * 1e9,
                busy_us=d["t_wake_standby_us"] + 6 * d["t_conv_us"] + cyc / d["f_MHz"])


def trace2_area():
    t = (REPO / "docs/rev10_1_nominal.cir").read_text()
    tft = [(float(w), float(l)) for w, l in re.findall(r"^X\S+\s+\S+\s+\S+\s+\S+\s+potft(?:seg)?\s+W=(\S+)\s+L=(\S+)", t, re.M)]
    caps = [float(c) for c in re.findall(r"^C\S+\s+\S+\s+\S+\s+([0-9.]+)p\b", t, re.M)]
    ci_F_per_mm2 = 0.70e-6 / 100.0                        # 1 cm^2 = 100 mm^2
    a_tft = sum(w * l for w, l in tft) * 1e-6             # um^2 -> mm^2
    a_cap = sum(c * 1e-12 for c in caps) / ci_F_per_mm2
    return dict(n_tft=len(tft), tft_channel_mm2=round(a_tft, 3), capacitors_pF=round(sum(caps), 1), capacitor_mm2=round(a_cap, 3),
                active_mm2_lower_bound=round(a_tft + a_cap, 3),
                note="channel area of every TFT (W x L) + every capacitor at C_i = 0.70 uF/cm^2; no overlap, contacts, "
                     "spacing, routing, pads; a lower bound on the die area, not a layout")


def main():
    c1 = json.loads((REPO / "results/host_v2/summary/c1_nominal.json").read_text())
    e_die = c1["energy_v2"]["total_net_nJ"]["median"]
    t_busy = c1["t_read_us"]["median"]
    cal = c1["calibration_session_energy_nJ"]["total"]
    m430 = {k: msp430(v) for k, v in CYCLES.items()}
    mm0 = {k: mspm0(v) for k, v in CYCLES.items()}
    d = MSP430
    host_lpm0_1MHz = t_busy * 1e-6 * d["I_LPM0_1MHz_uA"] * 1e-6 * d["V"] * 1e9
    host_lpm0_8MHz = t_busy * 1e-6 * d["I_LPM0_8MHz_uA"] * 1e-6 * d["V"] * 1e9
    host_adc = msp430(0)["adc_nJ"] + msp430(0)["wake_nJ"]
    out = dict(
        sources=dict(MSP430=MSP430, MSPM0=MSPM0, cycles_assumption=CYCLES),
        mcu_per_classification_nJ=dict(MSP430FR2433=m430, MSPM0L1306=mm0),
        mcu_standby=dict(MSP430FR2433_LPM3_uW=d["I_LPM3_VLO_uA"] * d["V"], MSP430FR2433_LPM4_uW=d["I_LPM4_uA"] * d["V"],
                         MSP430FR2433_LPM45_uW=d["I_LPM45_uA"] * d["V"], MSPM0L1306_standby_uW=MSPM0["I_standby_uA"] * MSPM0["V"],
                         MSPM0L1306_shutdown_uW=MSPM0["I_shutdown_uA"] * MSPM0["V"]),
        trace2=dict(die_energy_nJ_median=e_die, source_die="H2-02, results/host_v2/summary/c1_nominal.json",
                    host_busy_us_median=t_busy, source_busy="results/host_v2/summary/c1_nominal.json t_read_us (median)",
                    calibration_session_nJ=cal, die_standby_uW=0.0,
                    host_floor_during_classification_nJ=dict(
                        LPM0_1MHz_timer_only=host_lpm0_1MHz, LPM0_8MHz=host_lpm0_8MHz,
                        note="MSP430FR2433 kept in LPM0 with its clock running for the median read time; excludes the "
                             "analog drivers for V1/V2 (two DAC levels on 6-7 rows), the power switch, the I_DD meter "
                             "and the 6 ADC conversions the host needs anyway to form x"),
                    host_adc_and_wake_nJ=host_adc,
                    system_floor_nJ=e_die + host_lpm0_1MHz + host_adc,
                    area=trace2_area(),
                    host_lines=dict(driven=10, outputs=5, supply=1, note="SPEC 4.1: VDD, row1-6, rstr, rstb, phib, phi; na1-5")),
    )
    out["comparison"] = dict(
        mcu_nominal_total_nJ=dict(MSP430FR2433=m430["nominal"]["total_nJ"], MSPM0L1306=mm0["nominal"]["total_nJ"]),
        trace2_die_only_nJ=e_die,
        trace2_system_floor_nJ=out["trace2"]["system_floor_nJ"],
        ratio_trace2_system_floor_over_msp430_nominal=out["trace2"]["system_floor_nJ"] / m430["nominal"]["total_nJ"],
        mcu_standby_energy_at_1_per_s_uJ=d["I_LPM3_VLO_uA"] * d["V"] * 1.0,
    )
    (WU / "summary/s4_mcu.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out["comparison"], indent=1))
    print(json.dumps({k: {kk: round(vv, 1) for kk, vv in v.items()} for k, v in m430.items()}, indent=1))
    print(json.dumps(out["trace2"]["area"], indent=1), json.dumps(out["trace2"]["host_floor_during_classification_nJ"], indent=1))


if __name__ == "__main__":
    main()
