In this repository you find the files for the pico-vault challenge, all personalized based on the ID of the pico2.
To identify the ID of your pico2, you can use `lsusb verbose`:

```
$ lsusb -d 2e8a: -v | grep Serial
  iSerial                 3 0CDB480444AAE770
```

Or you can use `picotool info -d` when it is in `BOOTSEL` mode. 
For example, the output will be something like this:

```
$ picotool info -df
Tracking device serial number C97033E01601FDC4 for reboot
The device was asked to reboot into BOOTSEL mode so the command can be executed.


Device Information
 type:                 RP2350
 package:              QFN60
 chipid:               0xc97033e01601fdc4
 flash devinfo:        0x0c00
 current cpu:          ARM
 available cpus:       ARM
 secure boot:          1
 debug enable:         1
 secure debug enable:  1
 flash size:           4096K

                       The device was asked to reboot back into application mode.
```

You can find the files corresponding to your chipid in `personalized/`.

To help you solving the challenge and checking your solution, there are some scripts in `scripts/`.

If you need to reflash the firmware, put the device into `BOOTSEL` mode (with `picotool` or by holding `BOOTSEL` button before plugging in), and then copy the `.uf2` file of your Pico ID to your Pico.

Your objectives: 

1. Reverse protection mechanism
2. Recover PIN (using cryptographic operations)
3. Obtain secret key
4. Post the secret screen with your unique values to the report

Document everything in maximum 6 pages. 

Workflow and tips: 

1. Connect the Pico to your computer and try to communicate with the Pico Vault.
2. Figure out how the PIN is verified. 
  - You will need to do some reverse engineering!
  - For your Pico ID, only the `.uf2` file is available. This is the firmware flashing format used by Pico. The `scripts/uf2_to_bin.py` can transform this to a raw binary for you, which can be loaded into Ghidra and reverse engineered.
  - Reverse engineering the raw binary is hard, because there are no symbols or other annotations available. To help you, for the Pico ID `0000000000000000`, the `.elf` file is also available, which contains a lot more metadata such as function signatures.
  - The firmware for `0000000000000000` contains real values, but specific to that Pico ID, so they will not work recover the PIN for your Pico. Once you have figured out how to bruteforce the PIN, find the values needed for the bruteforce in the raw binary of your own Pico.
3. Implement an offline bruteforce for the PIN.
  - In `scripts/pico_vault_bf_partial.py` there is already the start of a bruteforce script in Python. Figure out how to finish it.
    - All to-be-implemented parts are marked with `# Finish this`.
  - Start with how to verify a single entry, then finish the bruteforcer.
  - To verify your implementation, there might be some test vectors in the firmware.
  - The pin for Pico ID `0000000000000000` is `00000000`.
4. If you have found the PIN, enter it to the Pico Vault, and recover the private key!
  - You can check that the result is correct with `scripts/pico_vault_key_validate.py`. Give this script the private key you found in the Pico Vault, and the `ec_public.pem` corresponding to your Pico ID.

