# Testing Checklist

---

## Before starting

- [ ] Activate the new environment: `conda activate app`
- [ ] Launch the app: `python gw_data_plotter.py`
- [ ] App opens without errors or warnings in the terminal

---

## Tab 1 — Get Data

### Download by GPS interval
- [ ] Select a detector (e.g. LIGO-Hanford)
- [ ] Enter a valid GPS start/stop (e.g. 2–4s interval around a known event)
- [ ] Click "Download data" → success message in log

### Download by known GW event (dropdown)
- [ ] Select a known event from the dropdown (e.g. GW150914)
- [ ] Click "Download data" → log shows event info + detectors available

### Download by typed event name
- [ ] Type an event name manually (e.g. GW200129_065458)
- [ ] Click "Download data" → success

### Download by known glitch
- [ ] Select a glitch type (e.g. Blip)
- [ ] Click "Download data" → success

### Save data
- [ ] Save as `.hdf5`
- [ ] Save as `.txt`
- [ ] Save as `.gwf`

### Load data
- [ ] Load a previously saved `.hdf5` file
- [ ] Load a previously saved `.txt` file
- [ ] Load a previously saved `.gwf` file
- [ ] Load an `.hdf5` file downloaded directly from GWOSC

### Edge cases
- [ ] Click "Download" with no detector selected → warning shown
- [ ] Click "Save data" before downloading → warning shown
- [ ] Enter invalid GPS times → error handled gracefully

---

## Tab 2 — Plot Data

### Strain plot
- [ ] Plot raw strain (no whitening, no freq selection)
- [ ] Plot with whitening enabled
- [ ] Plot with bandpass filter (set fmin/fmax)
- [ ] Plot with time zoom (adjust sliders)
- [ ] Combination: whiten + bandpass + zoom

### Q-scan plot
- [ ] Plot Qscan with default settings
- [ ] Plot with log y-axis enabled
- [ ] Plot with a custom Emax value
- [ ] Check colorbar starts from 0
- [ ] Update an existing Qscan plot (re-click button → window updates, no duplicate)

---

## Tab 3 — Explore GW Event Parameters

### Get event parameters
- [ ] Select a showcase event from dropdown → click "Get event parameters" → parameters displayed
- [ ] Type an event name manually → parameters displayed
- [ ] Check skymap download works

### Histogram
- [ ] Click "Plot histogram" → downloads catalog + plots
- [ ] Try different parameters (Mass 1, Chirp Mass, Luminosity Distance, etc.)
- [ ] Enable log x-axis
- [ ] Enable log y-axis
- [ ] Enable "highlight selected event" checkbox → event marked on histogram

### Scatter plot
- [ ] Click "2D scatter plot" → plots correctly
- [ ] Try different parameter combinations
- [ ] Enable log axes
- [ ] Enable "highlight selected event" checkbox

---

## General UI
- [ ] Help button on each tab opens the correct help window
- [ ] Re-clicking help raises existing window (no duplicate)
- [ ] "About" menu item opens the about dialog
- [ ] Fonts render correctly (Montserrat)
- [ ] In any plot window, click the save icon in the toolbar → save dialog opens → save as PNG/PDF/SVG works
