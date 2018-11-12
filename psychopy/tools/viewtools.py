#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tools for working with view projections for 2- and 3-D rendering.

"""

# Part of the PsychoPy library
# Copyright (C) 2018 Jonathan Peirce
# Distributed under the terms of the GNU General Public License (GPL).

import numpy as np
from collections import namedtuple

# convenient named tuple for storing frustum parameters
Frustum = namedtuple(
    'Frustum',
    ['left', 'right', 'bottom', 'top', 'nearVal', 'farVal'])


def computeFrustum(scrWidth,
                   scrAspect,
                   scrDist,
                   convergeOffset=0.0,
                   eyeOffset=0.0,
                   nearClip=0.01,
                   farClip=100.0):
    """Calculate frustum parameters for rendering stimuli with perspective. If
    an eye offset is provided, an asymmetric frustum is returned which can be
    used for stereoscopic rendering.

    Parameters
    ----------
    scrWidth : float
        The display's width in meters.
    scrAspect : float
        Aspect ratio of the display (width / height).
    scrDist : float
        Distance to the screen from the view in meters. Measured from the center
        of their eyes.
    convergeOffset : float
        Offset of the convergence plane from the screen. Objects falling on this
        plane will have zero disparity. For best results, the convergence plane
        should be set to the same distance as the screen (0.0 by default).
    eyeOffset : float
        Half the inter-ocular separation (i.e. the horizontal distance between
        the nose and center of the pupil) in meters. If eyeOffset is 0.0, a
        symmetric frustum is returned.
    nearClip : float
        Distance to the near clipping plane in meters from the viewer. Should be
        at least less than scrDist.
    farClip : float
        Distance to the far clipping plane from the viewer in meters. Must be
        >nearClip.

    Returns
    -------
    Frustum
        Namedtuple with frustum parameters. Can be directly passed to
        glFrustum (e.g. glFrustum(*f)).

    Notes
    -----
    The view point must be transformed for objects to appear correctly. Offsets
    in the X-direction must be applied +/- eyeOffset to account for inter-ocular
    separation. A transforqmation in the Z-direction must be applied to account
    for screen distance. These offsets MUST be applied to the MODELVIEW matrix,
    not the PROJECTION matrix! Doing so may break lighting calculations.

    """
    d = scrWidth * (convergeOffset + scrDist)
    ratio = nearClip / float((convergeOffset + scrDist))

    right = (d - eyeOffset) * ratio
    left = (d + eyeOffset) * -ratio
    top = (scrWidth / float(scrAspect)) * nearClip
    bottom = -top

    return Frustum(left, right, bottom, top, nearClip, farClip)


def generalPerspectiveProjection(posBottomLeft,
                                 posBottomRight,
                                 posTopLeft,
                                 eyePos,
                                 nearClip=0.01,
                                 farClip=100.0):
    """Generalized derivation of projection and view matrices based on the
    physical configuration of the display system.

    This implementation is based on Robert Kooima's 'Generalized Perspective
    Projection' (see http://csc.lsu.edu/~kooima/articles/genperspective/)
    method.

    Parameters
    ----------
    posBottomLeft : list of float or ndarray
        Bottom-left 3D coordinate of the screen in meters.
    posBottomRight : list of float or ndarray
        Bottom-right 3D coordinate of the screen in meters.
    posTopLeft : list of float or ndarray
        Top-left 3D coordinate of the screen in meters.
    eyePos : list of float or ndarray
        Coordinate of the eye in meters.
    nearClip : float
        Near clipping plane distance from viewer in meters.
    farClip : float
        Far clipping plane distance from viewer in meters.

    Returns
    -------
    tuple
        The 4x4 projection and view matrix.

    Notes
    -----
    The resulting projection frustums are off-axis relative to the center of the
    display.

    """
    # convert everything to numpy arrays
    posBottomLeft = np.asarray(posBottomLeft, np.float32)
    posBottomRight = np.asarray(posBottomRight, np.float32)
    posTopLeft = np.asarray(posTopLeft, np.float32)
    eyePos = np.asarray(eyePos, np.float32)

    # orthonormal basis of the screen plane
    vr = posBottomRight - posBottomLeft
    vr /= np.linalg.norm(vr)
    vu = posTopLeft - posBottomLeft
    vu /= np.linalg.norm(vu)
    vn = np.cross(vr, vu)
    vn /= np.linalg.norm(vn)

    # screen corner vectors
    va = posBottomLeft - eyePos
    vb = posBottomRight - eyePos
    vc = posTopLeft - eyePos

    dist = -np.dot(va, vn)
    nearOverDist = nearClip / dist
    left = float(np.dot(vr, va) * nearOverDist)
    right = float(np.dot(vr, vb) * nearOverDist)
    bottom = float(np.dot(vu, va) * nearOverDist)
    top = float(np.dot(vu, vc) * nearOverDist)

    # projection matrix to return
    projMat = perspectiveProjectionMatrix(
        left, right, bottom, top, nearClip, farClip)

    # view matrix to return, first compute the rotation component
    rotMat = np.zeros((4, 4), np.float32)
    rotMat[:3, 0] = vr
    rotMat[:3, 1] = vu
    rotMat[:3, 2] = vn
    rotMat[3, 3] = 1.0

    transMat = np.zeros((4, 4), np.float32)
    np.fill_diagonal(transMat, 1.0)
    transMat[3, :3] = -eyePos

    return projMat, np.matmul(transMat, rotMat)


def orthoProjectionMatrix(left, right, bottom, top, near, far):
    """Compute an orthographic projection matrix with provided frustum
    parameters.

    Parameters
    ----------
    left : float
        Left clipping plane coordinate.
    right : float
        Right clipping plane coordinate.
    bottom : float
        Bottom clipping plane coordinate.
    top : float
        Top clipping plane coordinate.
    near : float
        Near clipping plane distance from viewer.
    far : float
        Far clipping plane distance from viewer.

    Returns
    -------
    ndarray
        4x4 projection matrix

    """
    projMat = np.zeros((4, 4), np.float32)
    projMat[0, 0] = 2.0 / (right - left)
    projMat[1, 1] = 2.0 / (top - bottom)
    projMat[2, 2] = -2.0 / (far - near)
    projMat[3, 0] = (right + left) / (right - left)
    projMat[3, 1] = (top + bottom) / (top - bottom)
    projMat[3, 2] = (far + near) / (far - near)
    projMat[3, 3] = 1.0

    return projMat


def perspectiveProjectionMatrix(left, right, bottom, top, near, far):
    """Compute an perspective projection matrix with provided frustum
    parameters. The frustum can be asymmetric.

    Parameters
    ----------
    left : float
        Left clipping plane coordinate.
    right : float
        Right clipping plane coordinate.
    bottom : float
        Bottom clipping plane coordinate.
    top : float
        Top clipping plane coordinate.
    near : float
        Near clipping plane distance from viewer.
    far : float
        Far clipping plane distance from viewer.

    Returns
    -------
    ndarray
        4x4 projection matrix

    """
    projMat = np.zeros((4, 4), np.float32)
    projMat[0, 0] = (2.0 * near) / (right - left)
    projMat[1, 1] = (2.0 * near) / (top - bottom)
    projMat[2, 0] = (right + left) / (right - left)
    projMat[2, 1] = (top + bottom) / (top - bottom)
    projMat[2, 2] = -(far + near) / (far - near)
    projMat[2, 3] = -1.0
    projMat[3, 2] = -(2.0 * far * near) / (far - near)

    return projMat


def lookAt(eyePos, centerPos, upVec):
    """Create a transformation matrix to orient towards some point. Based on the
    same algorithm as 'gluLookAt'. This does not generate a projection matrix,
    but rather the matrix to transform the observer's view in the scene.

    For more information see:
    https://www.khronos.org/registry/OpenGL-Refpages/gl2.1/xhtml/gluLookAt.xml

    Parameters
    ----------
    eyePos : list of float or ndarray
        Eye position in the scene.
    centerPos : list of float or ndarray
        Position of the object center in the scene.
    upVec : list of float or ndarray
        Vector defining the up vector.

    Returns
    -------
    ndarray
        4x4 projection matrix

    """
    eyePos = np.asarray(eyePos, np.float32)
    centerPos = np.asarray(centerPos, np.float32)
    upVec = np.asarray(upVec, np.float32)

    f = centerPos - eyePos
    f /= np.linalg.norm(f)
    upVec /= np.linalg.norm(upVec)

    s = np.cross(f, upVec)
    u = np.cross(s / np.linalg.norm(s), f)

    rotMat = np.zeros((4, 4), np.float32)
    rotMat[:3, 0] = s
    rotMat[:3, 1] = u
    rotMat[:3, 2] = -f
    rotMat[3, 3] = 1.0

    transMat = np.zeros((4, 4), np.float32)
    np.fill_diagonal(transMat, 1.0)
    transMat[3, :3] = -eyePos

    return np.matmul(transMat, rotMat)