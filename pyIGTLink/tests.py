# -*- coding: utf-8 -*-
"""
Created on Thu Nov 12 09:58:10 2015

@author: Daniel Høyer Iversen
"""

import unittest

import numpy as np

import pyIGTLink

IGTL_HEADER_SIZE = 58


class TestServer(unittest.TestCase):
    """
    Tests the server
    """

    def setUp(self):     # pylint: disable=invalid-name
        """ things to be run when tests are started. """
        self.server = pyIGTLink.PyIGTLink(localServer=True)

    def tearDown(self):  # pylint: disable=invalid-name
        """ Stop down stuff we started. """
        self.server.close_server()

    def test_server(self):
        self.assertFalse(self.server.is_connected())
        self.assertEqual(self.server.get_ip_adress(), "127.0.0.1")
        self.assertEqual(self.server.get_port_no(), 18944)

    def test_add_msgs(self):
        samples = 500
        beams = 100
        k = 0

        for i in range(10):
            k = k+1
            data = np.random.randn(samples, beams)*50+100
            imageMessage = pyIGTLink.ImageMessage(data)
            self.assertTrue(self.server.add_message_to_send_queue(imageMessage))
        self.assertFalse(self.server.add_message_to_send_queue("invalidPackage"))
        self.assertFalse(self.server.add_message_to_send_queue(pyIGTLink.ImageMessage([1, 2, 3])))


class TestMsg(unittest.TestCase):
    """
    Tests the msg
    """

    def test_header_msg(self):
        msg = pyIGTLink.MessageBase()
        self.assertEqual(len(msg.get_binary_message()), IGTL_HEADER_SIZE)

    def test_image_msg(self):
        data = np.random.randn(500, 100)*50+100
        msg = pyIGTLink.ImageMessage(data)
        self.assertEqual(len(msg.get_binary_body()), msg.get_body_pack_size())
        self.assertEqual(len(msg.get_binary_message()), msg.get_body_pack_size() + IGTL_HEADER_SIZE)

    def test_transform_msg(self):
        data = np.random.randn(4, 4)
        msg = pyIGTLink.TransformMessage(data)
        self.assertEqual(len(msg.get_binary_body()), msg.get_body_pack_size())
        self.assertEqual(len(msg.get_binary_message()), msg.get_body_pack_size() + IGTL_HEADER_SIZE)

    def test_image_msg_matlab(self):
        data = np.random.randn(500*100, 1)*50+100
        msg = pyIGTLink.ImageMessageMatlab(data, [500, 100])
        self.assertEqual(len(msg.get_binary_body()), msg.get_body_pack_size())
        self.assertEqual(len(msg.get_binary_message()), msg.get_body_pack_size() + IGTL_HEADER_SIZE)


if __name__ == '__main__':
    unittest.main()
