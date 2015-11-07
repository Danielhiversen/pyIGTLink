# -*- coding: utf-8 -*-
"""
Created on Tue Nov  3 19:17:05 2015

@author: dahoiv
"""

 IGTL_IMAGE_HEADER_VERSION = 1


class Packet(object):
    pass



#http://openigtlink.org/protocols/v2_header.html
class ImageMessage(Packet):   
#    
#  # Sets image dimensions by an array of the numbers of pixels in i, j and k directions.
#  # SetDimensions() should be called prior to SetSubVolume(), since SetDimensions()
#  # sets subvolume parameters automatically assuming that subvolume = entire volume.
#  def SetDimensions(int s[3]):
#
#  # Sets image dimensions by the numbers of pixels in i, j and k directions.
#  # SetDimensions() should be called prior to SetSubVolume(), since SetDimensions()
#  # sets subvolume parameters automatically assuming that subvolume = entire volume.
#  def SetDimensions(int i, int j, int k):
#
#  # Gets image dimensions as an array of the numbers of pixels in i, j and k directions.
#  def GetDimensions(int s[3]):
#
#  # Gets image dimensions as the numbers of pixels in i, j and k directions.
#  def GetDimensions(int &i, int &j, int &k):
#  
#  # Sets sub-volume dimensions and offset by arrays of the dimensions and the offset.
#  # SetSubVolume() should be called after calling SetDiemensions(), since SetDimensions()
#  # reset the subvolume parameters automatically. Returns non-zero value if the subvolume
#  # is successfully specified. Returns zero, if invalid subvolume is specified.
#  def SetSubVolume(int dim[3], int off[3]):
#
#  # Sets sub-volume dimensions and offset by the dimensions and the offset in i, j and k
#  # directions. SetSubVolume() should be called after calling SetDiemensions(),
#  # since SetDimensions() reset the subvolume parameters automatically.
#  # Returns non-zero value if the subvolume is successfully specified. 
#  # Returns zero, if invalid subvolume is specified.
#  def SetSubVolume(int dimi, int dimj, int dimk, int offi, int offj, int offk):
#
#  # Gets sub-volume dimensions and offset using arrays of the dimensions and the offset.
#  def GetSubVolume(int dim[3], int off[3]):
#
#  # Gets sub-volume dimensions and offset by the dimensions and the offset in i, j and k
#  # directions.
#  def GetSubVolume(int &dimi, int &dimj, int &dimk, int &offi, int &offj, int &offk):
#
#  # Sets spacings by an array of spacing values in i, j and k directions.
#  def SetSpacing(float s[3]):
#
#  # Sets spacings by spacing values in i, j and k directions.
#  def SetSpacing(float si, float sj, float sk):
#
#  # Gets spacings using an array of spacing values in i, j and k directions.
#  def GetSpacing(float s[3]):
#
#  # Gets spacings using spacing values in i, j and k directions.
#  def GetSpacing(float &si, float &sj, float &sk):
#
#  # Sets the coordinates of the origin by an array of positions along the first (R or L),
#  # second (A or P) and the third (S) axes.
#  def SetOrigin(float p[3]):
#
#  # Sets the coordinates of the origin by positions along the first (R or L), second (A or P)
#  # and the third (S) axes.
#  def SetOrigin(float px, float py, float pz):
#
#  # Gets the coordinates of the origin using an array of positions along the first (R or L),
#  # second (A or P) and the third (S) axes.
#  def GetOrigin(float p[3]):
#
#  # Gets the coordinates of the origin by positions along the first (R or L), second (A or P)
#  # and the third (S) axes.
#  def GetOrigin(float &px, float &py, float &pz):
#
#  # Sets the orientation of the image by an array of the normal vectors for the i, j
#  # and k indeces.
#  def SetNormals(float o[3][3]):
#
#  # Sets the orientation of the image by the normal vectors for the i, j and k indeces.
#  def SetNormals(float t[3], float s[3], float n[3]):
#
#  # Gets the orientation of the image using an array of the normal vectors for the i, j
#  # and k indeces.
#  def GetNormals(float o[3][3]):
#
#  # Gets the orientation of the image using the normal vectors for the i, j and k indeces.
#  def GetNormals(float t[3], float s[3], float n[3]):
#
#  # Sets the number of components for each voxel.
#  def SetNumComponents(int num):
#
#  # Gets the number of components for each voxel.
#  def GetNumComponents():
#
#  # Sets the origin/orientation matrix.
#  def SetMatrix(Matrix4x4& mat):
#
#  # Gets the origin/orientation matrix.
#  def GetMatrix(Matrix4x4& mat):
#
#  # Sets the image scalar type.
#  def SetScalarType(int t)    { scalarType = t: }:
#
#  # Sets the image scalar type to 8-bit integer.
#  def SetScalarTypeToInt8()   { scalarType = TYPE_INT8: }:
#
#  # Sets the image scalar type to unsigned 8-bit integer.
#  def SetScalarTypeToUint8()  { scalarType = TYPE_UINT8: }:
#
#  # Sets the image scalar type to 16-bit integer.
#  def SetScalarTypeToInt16()  { scalarType = TYPE_INT16: }:
#
#  # Sets the image scalar type to unsigned 16-bit integer.
#  def SetScalarTypeToUint16() { scalarType = TYPE_UINT16: }:
#
#  # Sets the image scalar type to 32-bit integer.
#  def SetScalarTypeToInt32()  { scalarType = TYPE_INT32: }:
#
#  # Sets the image scalar type to unsigned 32-bit integer.
#  def SetScalarTypeToUint32() { scalarType = TYPE_UINT32: }:
#
#  # Gets the image scalar type.
#  def  GetScalarType()         { return scalarType: }:
#
#  # Gets the size of the scalar type used in the current image data.
#  # (e.g. 1 byte for 8-bit integer)
#  int  GetScalarSize()         { return ScalarSizeTable[scalarType]: }:
#
#  # Gets the size of the specified scalar type. (e.g. 1 byte for 8-bit integer)
#  int  GetScalarSize(int type) { return ScalarSizeTable[type]: }:
#
#  # Sets the Endianess of the image scalars. (default is ENDIAN_BIG)
#  def SetEndian(int e)        { endian = e: }:
#
#  # Gets the Endianess of the image scalars.
#  int  GetEndian()             { return endian: }:
#
#  # Gets the size (length) of the byte array for the image data.
#  # The size is defined by dimensions[0]*dimensions[1]*dimensions[2]*scalarSize*numComponents.
#  # TODO: Should returned value be 64-bit integer?
#  int  GetImageSize()
#  {
#    return dimensions[0]*dimensions[1]*dimensions[2]*GetScalarSize()*numComponents:
#  }:
#
#  # Returns coordinate system (COORDINATE_RAS or COORDINATE_LPS)
#  int GetCoordinateSystem() { return coordinate:}:
#
#  # Sets coordinate system (COORDINATE_RAS or COORDINATE_LPS)
#  def SetCoordinateSystem(int c) {coordinate = c:}:
#
#
#  # Gets the size (length) of the byte array for the subvolume image data.
#  # The size is defined by subDimensions[0]*subDimensions[1]*subDimensions[2]*
#  # scalarSize*numComponents.
#  def  GetSubVolumeImageSize():
#
#
#  # Allocates a memory area for the scalar data based on the dimensions of the subvolume,
#  # the number of components, and the scalar type.
#  def  AllocateScalars():
#
#  # Gets a pointer to the scalar data.
#  def GetScalarPointer():