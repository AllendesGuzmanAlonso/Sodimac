"""Creacion de modelos iniciales

Revision ID: 70c914be84ba
Revises: 
Create Date: 2024-10-07 23:59:35.456989

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '70c914be84ba'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('sucursales',
    sa.Column('id_sucursal', sa.Integer(), nullable=False),
    sa.Column('nombre_sucursal', sa.String(length=100), nullable=False),
    sa.Column('ubicacion', sa.String(length=200), nullable=False),
    sa.PrimaryKeyConstraint('id_sucursal')
    )
    op.create_table('usuarios',
    sa.Column('id_usuario', sa.Integer(), nullable=False),
    sa.Column('nombre', sa.String(length=100), nullable=False),
    sa.Column('correo', sa.String(length=120), nullable=False),
    sa.Column('rol', sa.Enum('USUARIO', 'ADMINISTRADOR', name='rolenum'), nullable=False),
    sa.Column('password_hash', sa.String(length=128), nullable=False),
    sa.PrimaryKeyConstraint('id_usuario'),
    sa.UniqueConstraint('correo')
    )
    op.create_table('herramientas',
    sa.Column('id_herramienta', sa.Integer(), nullable=False),
    sa.Column('nombre', sa.String(length=100), nullable=False),
    sa.Column('marca', sa.String(length=50), nullable=False),
    sa.Column('codigo', sa.String(length=50), nullable=False),
    sa.Column('estado', sa.Enum('DISPONIBLE', 'RESERVADA', 'EN_REPARACION', name='estadoherramientaenum'), nullable=False),
    sa.Column('cantidad_disponible', sa.Integer(), nullable=False),
    sa.Column('sucursal_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['sucursal_id'], ['sucursales.id_sucursal'], ),
    sa.PrimaryKeyConstraint('id_herramienta'),
    sa.UniqueConstraint('codigo')
    )
    op.create_table('herramienta_sucursal',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('herramienta_id', sa.Integer(), nullable=False),
    sa.Column('sucursal_id', sa.Integer(), nullable=False),
    sa.Column('cantidad_disponible', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['herramienta_id'], ['herramientas.id_herramienta'], ),
    sa.ForeignKeyConstraint(['sucursal_id'], ['sucursales.id_sucursal'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('reporte_arriendos',
    sa.Column('id_arriendo', sa.Integer(), nullable=False),
    sa.Column('id_usuario', sa.Integer(), nullable=False),
    sa.Column('id_herramienta', sa.Integer(), nullable=False),
    sa.Column('fecha_inicio', sa.DateTime(), nullable=False),
    sa.Column('fecha_fin', sa.DateTime(), nullable=True),
    sa.Column('estado_arriendo', sa.Enum('EN_PROCESO', 'FINALIZADO', name='estadoarriendoenum'), nullable=False),
    sa.ForeignKeyConstraint(['id_herramienta'], ['herramientas.id_herramienta'], ),
    sa.ForeignKeyConstraint(['id_usuario'], ['usuarios.id_usuario'], ),
    sa.PrimaryKeyConstraint('id_arriendo')
    )
    op.create_table('transacciones',
    sa.Column('id_transaccion', sa.Integer(), nullable=False),
    sa.Column('id_herramienta', sa.Integer(), nullable=False),
    sa.Column('tipo', sa.String(length=50), nullable=False),
    sa.Column('fecha', sa.DateTime(), nullable=False),
    sa.Column('cantidad', sa.Integer(), nullable=False),
    sa.Column('sucursal_origen', sa.Integer(), nullable=True),
    sa.Column('sucursal_destino', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['id_herramienta'], ['herramientas.id_herramienta'], ),
    sa.ForeignKeyConstraint(['sucursal_destino'], ['sucursales.id_sucursal'], ),
    sa.ForeignKeyConstraint(['sucursal_origen'], ['sucursales.id_sucursal'], ),
    sa.PrimaryKeyConstraint('id_transaccion')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('transacciones')
    op.drop_table('reporte_arriendos')
    op.drop_table('herramienta_sucursal')
    op.drop_table('herramientas')
    op.drop_table('usuarios')
    op.drop_table('sucursales')
    # ### end Alembic commands ###
