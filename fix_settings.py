import os

filepath = r'c:\Users\simed\Downloads\AdminLTE-3.2.0-rc\proyectoDWA\config\settings.py'

# Read as raw bytes to handle the mixed encoding
with open(filepath, 'rb') as f:
    raw_content = f.read()

# The null bytes were introduced by PowerShell UTF-16 LE append.
# We can just remove the null bytes (\x00) assuming the text was ASCII-compatible.
# Also we should probably decode it properly if possible, but stripping null bytes works for ASCII.
cleaned_content = raw_content.replace(b'\x00', b'')

# Save it back as UTF-8
with open(filepath, 'wb') as f:
    f.write(cleaned_content)

print("Fixed settings.py")
