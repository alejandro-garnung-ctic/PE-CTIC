#!/bin/bash
mkdir -p backups
cp -r shared backups/shared_backup_$(date +%Y%m%d_%H%M%S)
cp -r users backups/users_backup_$(date +%Y%m%d_%H%M%S)
echo "Backups hechos"
