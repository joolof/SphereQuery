# SphereQuery

![example](screenshots/SphereQuery.png)

Package to browse and explore the ESO VLT/SPHERE archive.

## Requirements

The requirements can be found below. The main interface is done using `PyQt5`, while the query to the ESO SPHERE archive is done using `astroquery`. There are some scripts that come directly from the ESO webpages (`eso_programmatic.py`) which are using the `pyvo` package.

I also included a script to have a first look reduction of the ADI observations. The file `data_reduction.py` will be copied to the directory where the data has been downloaded, and can be run from there. This scripts makes use of the `vlt-sphere` package from @avigan.

```python

astropy==5.0.4
astroquery==0.4.6
imutils==0.5.4
numpy==1.17.4
PyQt5==5.15.9
pyvo==1.3
requests==2.22.0
scikit_learn==1.2.2
vlt_sphere==1.5.1

```


