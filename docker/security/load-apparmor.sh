#!/bin/bash

# Check if AppArmor is available
if ! command -v apparmor_parser &> /dev/null; then
    echo "AppArmor is not installed. Skipping profile loading."
    exit 0
fi

# Check if AppArmor is enabled
if [ ! -d /sys/kernel/security/apparmor ]; then
    echo "AppArmor is not enabled in the kernel. Skipping profile loading."
    exit 0
fi

# Load the AppArmor profile
echo "Loading AppArmor profile for social media application..."
sudo apparmor_parser -r -W ./security/apparmor-profile

# Check if the profile was loaded successfully
if [ $? -eq 0 ]; then
    echo "AppArmor profile loaded successfully."
else
    echo "Failed to load AppArmor profile."
    exit 1
fi

# Check if the profile is loaded
if sudo aa-status | grep -q "docker-social-media"; then
    echo "Profile docker-social-media is active."
else
    echo "Warning: Profile docker-social-media is not active."
fi

exit 0 