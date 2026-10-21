# Problem Statement

## Background
Green coffee beans are sorted by hand in many farms and processing centers. Manual visual
sorting is slow, tiring, and inconsistent between workers, which can lower coffee quality.

## Problem
There is no simple, accessible tool that sorters can use to check a bean's category
consistently from an image.

## Proposed solution
A mobile app where the user captures or uploads a photo of a single green bean and gets a
predicted category (Peaberry, Longberry, Premium, Defect) with a confidence score.

## Data mining questions (draft — to be finalized in Step 2)
1. Can a CNN trained on bean images classify the 4 categories accurately enough to assist sorters? (classification)
2. How reliably does the model separate **Defect** beans from good beans? (binary view of the same classifier)
3. Which categories get confused with each other most, and why? (error analysis on the confusion matrix)
4. Does accuracy hold up on photos taken with a phone, not just the dataset images? (generalization test)
