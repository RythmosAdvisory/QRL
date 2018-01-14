from qrl.core.misc import logger
from qrl.core.Block import Block
from qrl.core.p2pObserver import P2PBaseObserver
from qrl.generated import qrllegacy_pb2, qrl_pb2


class P2PChainManager(P2PBaseObserver):
    def __init__(self):
        super().__init__()

    def new_channel(self, channel):
        channel.register(qrllegacy_pb2.LegacyMessage.FB, self.handle_fetch_block)
        channel.register(qrllegacy_pb2.LegacyMessage.PB, self.handle_push_block)
        channel.register(qrllegacy_pb2.LegacyMessage.BH, self.handle_block_height)

    def handle_fetch_block(self, source, message: qrllegacy_pb2.LegacyMessage):  # Fetch Request for block
        """
        Fetch Block
        Sends the request for the block.
        :return:
        """
        P2PBaseObserver._validate_message(message, qrllegacy_pb2.LegacyMessage.FB)

        block_number = message.fbData.index

        logger.info(' Request for %s by %s', block_number, source.connection_id)
        if 0 < block_number <= source.factory.chain_height:
            block = source.factory.get_block(block_number)
            msg = qrllegacy_pb2.LegacyMessage(func_name=qrllegacy_pb2.LegacyMessage.PB,
                                              pbData=qrllegacy_pb2.PBData(block=block.pbdata))
            source.send(msg)

    def handle_push_block(self, source, message: qrllegacy_pb2.LegacyMessage):
        """
        Push Block
        This function processes requested blocks received while syncing.
        Block received under this function are directly added to the main
        chain i.e. chain.blockchain
        It is expected to receive only one block for a given blocknumber.
        :return:
        """
        # FIXME: Later rename
        P2PBaseObserver._validate_message(message, qrllegacy_pb2.LegacyMessage.PB)
        if message.pbData is None:
            return

        try:
            block = Block(message.pbData.block)
            source.factory.block_received(block)

        except Exception as e:
            logger.error('block rejected - unable to decode serialised data %s', source.peer_ip)
            logger.exception(e)

    def handle_block_height(self, source, message: qrllegacy_pb2.LegacyMessage):
        """
        Sends / Receives Blockheight
        :param source:
        :param message:
        :return:
        """
        if message.bhData.block_number == 0:
            block = source.factory.get_last_block()
            if block.block_number == 0:
                return
            bhdata = qrl_pb2.BlockHeightData(block_number=block.block_number,
                                             block_headerhash=block.headerhash)
            msg = qrllegacy_pb2.LegacyMessage(func_name=qrllegacy_pb2.LegacyMessage.BH,
                                              bhData=bhdata)
            source.send(msg)
        else:
            source.factory.update_peer_blockheight(source.connection_id,
                                                   message.bhData.block_number,
                                                   message.bhData.block_headerhash)