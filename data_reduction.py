import os
import imutils
import subprocess
import numpy as np
from astropy.io import fits
import sphere.IRDIS as IRDIS
from sklearn.decomposition import PCA
# ------------------------------------------------------------

def do_reduction():
    reduction = IRDIS.ImagingReduction('./', log_level='info')
    reduction.config['combine_psf_dim']          = 64
    reduction.config['combine_science_dim']      = 300
    reduction.config['combine_shift_method']     = 'fft'
    reduction.config['preproc_collapse_science'] = False
    reduction.config['preproc_collapse_type']    = 'mean'
    reduction.full_reduction()

def get_images(maindir = './'):
    """
    Method to read the observations.
    """
    dopca = True
    if os.path.isfile(maindir + '/products/science_cube.fits'):
        """
        Read the datacube
        """
        hdulist = fits.open(maindir + '/products/science_cube.fits')
        adi = hdulist[0].data
        hdulist.close()
        if len(np.shape(adi)) == 4:
            adi = np.median(adi, axis = 0)
        """
        Read the angles
        """
        hdulist = fits.open(maindir + '/products/science_derot.fits')
        theta = hdulist[0].data
        hdulist.close()
    elif os.path.isfile(maindir + '/products/starcenter_cube.fits'):
        """
        Read the datacube
        """
        hdulist = fits.open(maindir + '/products/starcenter_cube.fits')
        adi = hdulist[0].data
        hdulist.close()
        if len(np.shape(adi)) == 4:
            adi = np.median(adi, axis = 0)
        """
        Read the angles
        """
        hdulist = fits.open(maindir + '/products/starcenter_derot.fits')
        theta = hdulist[0].data
        hdulist.close()
    else:
        dopca = False

    destination = maindir + '/reduced/'
    mkdir(destination)
    if dopca:
        for i in range(5):
            pca = get_pca(adi, theta, i+1)
            fits.writeto(maindir + '/reduced/pca_' + str(i+1) + '.fits', pca, overwrite = True)


"""
Compute pca for the datacube im_arr
"""
def get_pca(im_arr, theta, klip):
    """
    Method to compute the PCA of a datacube.
    """
    ntheta = im_arr.shape[0]
    nx = im_arr.shape[1]
    # --------------------------------------------------------------
    # Reshape the datacube        
    # --------------------------------------------------------------
    im_arr = im_arr.reshape(ntheta, nx * nx)
    pca_method = PCA(n_components=klip)
    psf_pca = pca_method.inverse_transform(pca_method.fit_transform(im_arr))
    psf_pca = psf_pca.reshape(ntheta, nx, nx)
    im_arr = im_arr.reshape(ntheta, nx, nx)
    # --------------------------------------------------------------
    # De-rotate the individual frames
    # --------------------------------------------------------------
    cube_derot = np.zeros(shape=(ntheta, nx, nx))
    for i in range(ntheta):
        cube_derot[i,] = imutils.rotate(im_arr[i,] - psf_pca[i,], -theta[i])
    # --------------------------------------------------------------
    # Take the median of the de-rotated cube
    # --------------------------------------------------------------
    pca = np.median(cube_derot,axis=0)
    return pca

"""
Method to check if there is a directory, and if not, create it.
"""
def mkdir(path):
    if not os.path.isdir(path):
        args = ['mkdir', path]
        mdir = subprocess.Popen(args).wait()

if __name__ == '__main__':
    if not os.path.isdir('products'):
        do_reduction()
    get_images()
