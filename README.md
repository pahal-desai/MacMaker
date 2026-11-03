<!-- trying to make it sound professional. thar doesnt mean that its all ai -->
# MacMaker

### Hackintoshing. No tutorials required.

MacMaker is an open-source project that aims to make Hackintoshing simpler, more approachable, and less intimidating.

Setting up macOS on PC hardware can involve hours of researching compatibility, configuring OpenCore, creating EFI folders, mapping USB ports, and troubleshooting cryptic errors.

MacMaker aims to bring these steps together into a guided desktop experience.

> **Status:** Early development. MacMaker is not ready for general use yet.

## The idea

i have a simple goal: make Hackintoshing understandable even for people who have never worked with OpenCore before.

MacMaker is being designed to help users:

- **Detect hardware** — Identify their pc components.
- **Check compatibility** — Understand hardware support and potential limitations.
- **Map USB ports** — Get guidance through the USB mapping process.
- **Generate EFI configurations** — Build hardware-specific OpenCore configurations using verified rules.
- **Prepare installation media** — Simplify macOS recovery and USB preparation.
- **Troubleshoot issues** — Make common errors easier to understand.

These are planned capabilities, not promises of currently available functionality.

## approach

MacMaker is intended to combine deterministic compatibility checks with clear, guided explanations.

Hardware compatibility decisions should be based on verified information and rules, not AI guesses. AI-assisted guidance may help explain documentation and troubleshooting, but it should never replace technical validation.

## Technology

The planned architecture includes:

- **Electron** — Desktop application.
- **HTML, CSS and JavaScript** — User interface.
- **Python** — Backend and system-level operations.
- **SQLite** — Local data storage.

The implementation may evolve as development progresses.

## Roadmap

- [x] Desktop application foundation
- [x] Hardware detection
- [ ] Hardware compatibility analysis
- [ ] Guided USB mapping
- [ ] OpenCore EFI generation
- [ ] macOS recovery preparation
- [ ] Guided installation workflow
- [ ] Troubleshooting assistance

## how to run it on your computer

if you want to test or run this app on your computer here is how you can do it. it is not very hard just follow these steps.

### stuff you need before starting
make sure you got these installed on your pc:
- node.js (grab it from nodejs website)
- python 3 (if you are on windows remember to check the box that says add python to path)

### steps to run it

1. clone the repo and go inside the folder:
```bash
git clone https://github.com/pahal-desai/MacMaker.git
cd MacMaker
```

2. install all the node stuff:
```bash
npm install
```

3. set up python virtual environment and get the packages:
- on linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install psutil py-cpuinfo
```
- on windows (in cmd or powershell):
```bat
python -m venv .venv
.venv\Scripts\activate
pip install psutil py-cpuinfo wmi
```

4. start the app:
```bash
npm start
```
and thats it. the app window will open up and you can click next to see your hardware specs.

### how to make the executable files

if you want to make the app into a file you can just click and open:

- for linux:
```bash
npm run build:linux
```
this makes an `.AppImage` file inside `dist` folder. you can just right click it, allow executing as program, and double click to run it.

- for windows:
```bash
npm run build:win
```
this makes a `.exe` file in `dist` folder. you can run it on windows without needing to install anything extra.

## Contributing

MacMaker is open source, and contributions are welcome.

You can contribute by:

- Reporting bugs and compatibility issues.
- Improving hardware detection and compatibility rules.
- Contributing to the documentation.
- Suggesting features.
- Submitting pull requests.

Check the repository for the latest development progress.

## Important notice

MacMaker is an independent community project and is not affiliated with, endorsed by, or supported by Apple Inc.

Installing macOS on non-Apple hardware may be restricted by Apple's software licence and applicable laws. Users are responsible for understanding and complying with the relevant terms and laws.

!! Hardware compatibility is not guaranteed !!

## License

See [LICENSE](LICENSE) for licensing information.

---